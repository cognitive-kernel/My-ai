from __future__ import annotations
import json
import time
import logging

from .curriculum import next_topic,canonical_language,LANGUAGE_CURRICULA
from .learning_sources import topic_source_urls, mark_sources_learned
from .advanced_curriculum import seed_for
from .db import execute,fetch_all,search_knowledge
from .executor import run_python
from .llm import create_llm
from .self_update import recent_lessons
from .memory import remember
from .web_learner import WebLearner
from .security import SecurityEngine
from .dast import LocalDAST
from .project_workspace import create_project_workspace, write_project_files
from .config import settings
from .settings_store import get_int

logger = logging.getLogger(__name__)

class LearningEngine:
    def __init__(self,llm=None):
        self.llm=llm or create_llm("general"); self.web=WebLearner()
        self.security=SecurityEngine(self.llm); self.dast=LocalDAST()

    def _retry_with_limit(self, operation, label, progress_callback=None, topic=None, stop_event=None, max_attempts=None):
        """Retry a learning operation up to the configured limit, respecting cancellation."""
        delay=1.0
        max_attempts=max(1,int(max_attempts or get_int("learning.max_retries",settings.learning_max_retries)))
        for attempt in range(1,max_attempts+1):
            if stop_event is not None and stop_event.is_set():
                raise InterruptedError("learning stopped")
            try:
                return operation()
            except Exception as exc:
                if stop_event is not None and stop_event.is_set():
                    raise InterruptedError("learning stopped") from exc
                if attempt >= max_attempts:
                    raise RuntimeError(f"{label} failed after {max_attempts} attempts: {exc}") from exc
                if progress_callback:
                    progress_callback("retrying", topic or label)
                if stop_event is not None:
                    stop_event.wait(delay)
                else:
                    time.sleep(delay)
                delay=min(delay*2.0,60.0)
        raise RuntimeError(f"{label} failed")

    def _retry_forever(self, operation, label, progress_callback=None, topic=None, stop_event=None):
        """Backward-compatible wrapper for callers using the previous retry method name."""
        return self._retry_with_limit(operation, label, progress_callback, topic, stop_event)

    def _discover_prerequisites(self,language,topic,progress_callback=None,stop_event=None):
        """Derive prerequisites locally; learning must not require a second model call."""
        if stop_event is not None and stop_event.is_set():
            raise InterruptedError("learning stopped")
        topic_name=str(topic.get("topic") or "").casefold()
        prerequisites=[]
        for item in LANGUAGE_CURRICULA.get(language, []):
            name=str(item.get("topic") or "")
            if not name or name.casefold()==topic_name:
                continue
            order=int(item.get("order") or 0)
            current_order=int(topic.get("order") or 0)
            if current_order and 0 < order < current_order:
                prerequisites.append({
                    "name":name,
                    "reason":"Earlier curriculum topic",
                    "recommended_order":order,
                })
        return prerequisites[-3:]

    @staticmethod
    def _parse_prerequisites(raw):
        data=json.loads(raw)
        return data.get("prerequisites",[]) if isinstance(data,dict) else []

    def _learn_sources_for_topic(self,language,topic,prerequisites,progress_callback=None,stop_event=None):
        knowledge=[]
        seed=seed_for(language,topic["topic"])
        if seed:
            remember(language,"Model knowledge seed: "+topic["topic"],seed,"model://knowledge-seed")
            knowledge.append({"title":"Model knowledge seed","url":"model://knowledge-seed"})
        # Each topic gets its own supplementary references first, then official
        # domain documentation. This prevents a broad domain source list from
        # replacing topic-specific learning material.
        topic_sources = topic_source_urls(language, topic["topic"])[:12]
        learned_urls=[]
        for url in topic_sources:
            def fetch_and_extract(url=url):
                title,source=self.web.fetch(url, stop_event=stop_event)
                # Web fetching is optional. Store the source as evidence; the single
                # lesson call later performs synthesis. This removes one LLM call per URL.
                compact_source=str(source)[:settings.learning_source_max_chars]
                return title,compact_source
            try:
                title,note=self._retry_with_limit(
                    fetch_and_extract,
                    "source",
                    progress_callback,
                    topic["topic"],
                    stop_event,
                    max_attempts=2,
                )
            except InterruptedError:
                raise
            except Exception as exc:
                message=str(exc)
                logger.warning(
                    "LEARNING_SOURCE_FAILURE: language=%s topic=%s url=%s error_type=%s error=%s",
                    language, topic["topic"], url, type(exc).__name__, message,
                )
                knowledge.append({"title":"Source unavailable","url":url,"error":message})
                if progress_callback:
                    progress_callback("source_unavailable",topic["topic"])
                continue
            remember(language,title,note,url); knowledge.append({"title":title,"url":url}); learned_urls.append(url)
        mark_sources_learned(language, topic["topic"], learned_urls)
        failed_sources = [item for item in knowledge if item.get("error")]
        if failed_sources:
            if progress_callback:
                progress_callback("source_fallback", topic["topic"])
            local = search_knowledge(language + " " + topic["topic"], 12)
            if local:
                knowledge.extend(
                    {"title": str(item.get("title") or "Local knowledge"),
                     "url": str(item.get("source_url") or "memory://knowledge")}
                    for item in local
                )
        return knowledge

    def study_url(self,url,topic="Python"):
        title,source=self.web.fetch(url)
        note=self.llm.chat(
            "Study the supplied source and produce a concise, accurate learning note. "
            "Use only information supported by the source; identify uncertainty instead of inventing facts. "
            f"\nTOPIC: {topic}\nSOURCE TITLE: {title}\nSOURCE URL: {url}\nSOURCE:\n{source}",
            system="You are a rigorous programming teacher."
        )
        remember(topic,title,note,url)
        return {"title":title,"url":url,"topic":topic,"content":note}

    def start(self,language="Python"):
        language=canonical_language(language)
        active=fetch_all("SELECT * FROM learning_sessions WHERE language=? AND status='started' ORDER BY id DESC LIMIT 1",(language,))
        if active:
            row=active[0]
            try: topic=json.loads(row["notes"] or "{}")
            except Exception: topic={}
            if topic.get("topic"):
                return {"status":"started","session_id":row["id"],"topic":topic}
        rows=fetch_all("SELECT topic FROM learning_sessions WHERE language=? AND status='completed'",(language,))
        topic=next_topic(language,{str(r["topic"]) for r in rows})
        if not topic:
            if language in LANGUAGE_CURRICULA:
                return {"status":"completed","message":f"{language} curriculum is complete."}
            topic={"order":1,"topic":language,"goal":f"Build a complete, source-backed learning track for {language}."}
        sid=execute("INSERT INTO learning_sessions(language,topic,status,notes,progress_percent,phase) VALUES(?,?,?,?,?,?)",(language,str(topic["topic"]),"started",json.dumps(topic,ensure_ascii=False),0.0,"starting"))
        return {"status":"started","session_id":sid,"topic":topic}

    def learn_next(self,language="Python",progress_callback=None,stop_event=None):
        language=canonical_language(language); s=self.start(language)
        if s["status"]=="completed": return s
        t=s["topic"]
        self._set_progress(s["session_id"], 0.5, "prerequisites")
        if progress_callback: progress_callback("prerequisites",t["topic"])
        try:
            prerequisites=self._discover_prerequisites(language,t,progress_callback,stop_event)
        except InterruptedError:
            raise
        except Exception as exc:
            # Prerequisite discovery is an enrichment step, not a hard dependency.
            # A temporary routing/model failure must not kill the learning worker.
            logger.warning(
                "prerequisite discovery failed; continuing without prerequisites: language=%s topic=%s error=%s",
                language,
                t["topic"],
                exc,
            )
            prerequisites=[]
        self._set_progress(s["session_id"], 25.0, "sources")
        if progress_callback: progress_callback("sources",t["topic"])
        sources=self._learn_sources_for_topic(language,t,prerequisites,progress_callback,stop_event)
        self._set_progress(s["session_id"], 50.0, "lesson")
        if progress_callback: progress_callback("lesson",t["topic"])
        seed=seed_for(language,t["topic"])
        logger.info("LEARNING_LESSON_START: language=%s topic=%s sources=%s", language, t["topic"], len(sources))
        lesson=self._retry_with_limit(
            lambda: self.llm.chat("Teach the topic as a complete, structured study unit. Include prerequisite lessons first, then the main topic, examples, exercises, tests, common mistakes, security considerations and a mastery checklist. "
                             "Use the model knowledge seed only as an initial layer; reconcile it with supplied official-source knowledge and explicitly correct conflicts. "
                             "Do not claim mastery unless supported by the supplied knowledge. Return clear sections.\n"
                             f"LANGUAGE: {language}\nTOPIC: {t['topic']}\nGOAL: {t['goal']}\n"
                             f"MODEL KNOWLEDGE SEED: {seed}\n"
                             f"DISCOVERED PREREQUISITES: {json.dumps(prerequisites,ensure_ascii=False)}\n"
                             f"LEARNED KNOWLEDGE: {json.dumps(search_knowledge(language+' '+t['topic'],12),ensure_ascii=False)}"),
            "lesson",progress_callback,t["topic"],stop_event,
        )
        logger.info("LEARNING_LESSON_SUCCESS: language=%s topic=%s chars=%s", language, t["topic"], len(lesson))
        remember(language,"Mastery lesson: "+t["topic"],lesson)
        self._set_progress(s["session_id"], 75.0, "assessment")
        if progress_callback: progress_callback("assessment",t["topic"])
        try:
            score=self._retry_with_limit(
                lambda: self.assess(t["topic"],lesson,allow_retry=False),
                "assessment",
                progress_callback,
                t["topic"],
                stop_event,
            )
        except InterruptedError:
            raise
        except Exception as exc:
            # Assessment must never erase a successfully generated lesson.
            # Keep the score nullable and let the next review re-assess it.
            logger.warning(
                "learning assessment unavailable; completing lesson without score: language=%s topic=%s error=%s",
                language,
                t["topic"],
                exc,
            )
            score=None
        execute("UPDATE learning_sessions SET status='completed',score=?,notes=?,progress_percent=100.0,phase='completed' WHERE id=?",(score,lesson,s["session_id"]))
        if progress_callback: progress_callback("completed",t["topic"])
        return {"status":"completed","session_id":s["session_id"],"language":language,"topic":t,"prerequisites":prerequisites,"score":score,"sources":sources,"seeded":bool(seed)}

    def autonomous_step(self,language="Python"): return self.learn_next(language)

    def assess(self,topic,lesson,allow_retry=True):
        """Deterministic coverage assessment; never adds another LLM dependency."""
        text=str(lesson or "").strip()
        if not text:
            return None
        required=("prerequisite","example","exercise","test","mistake","security","mastery")
        lowered=text.casefold()
        coverage=sum(1 for item in required if item in lowered) / len(required)
        length_score=min(1.0, len(text)/5000.0)
        section_bonus=0.15 if text.count("\n") >= 8 else 0.0
        score=(0.65*coverage + 0.25*length_score + section_bonus)*100.0
        return round(max(0.0,min(100.0,score)),1)

    @staticmethod
    def _set_progress(session_id, progress, phase):
        execute("UPDATE learning_sessions SET progress_percent=?, phase=? WHERE id=?",(max(0.0,min(100.0,float(progress))),phase,session_id))

    def practice(self,task,language="Python"):
        llm=create_llm("coding")
        return {"exercise":llm.chat(f"Create one {language} exercise. Return JSON keys description, starter_code, expected_behavior, hidden_tests. Task: {task}")}

    def generate_program(self,request,language="Python"):
        language=canonical_language(language); context=search_knowledge(language+" programming",20)
        coding_llm=create_llm("coding")
        lessons=recent_lessons(12)
        code=coding_llm.chat("Write a complete runnable "+language+" program for the user request. Use accumulated learning knowledge. "
                            "Apply secure coding practices, validate inputs, avoid unsafe defaults, include appropriate error handling and tests where practical. "
                            "Return ONLY source code.\nREQUEST: "+request+"\nKNOWLEDGE: "+json.dumps(context,ensure_ascii=False)+"\nRECENT SELF-REPAIR LESSONS: "+json.dumps(lessons,ensure_ascii=False),
                            system="You are a senior secure software engineer. Never claim execution unless a result is supplied.").strip()
        fence=chr(96)*3
        if code.startswith(fence):
            lines=code.splitlines()[1:]
            if lines and lines[-1].strip()==fence: lines=lines[:-1]
            code="\n".join(lines).strip()
        workspace=create_project_workspace(request)
        written_files=write_project_files(workspace,language,request,code)
        pid=execute("INSERT INTO generated_projects(language,request,code) VALUES(?,?,?)",(language,request,code))
        result={"language":language,"request":request,"code":code,"project_id":pid,
                "project_name":workspace.name,"project_path":str(workspace.relative_to(workspace.parents[1])),
                "files":written_files}
        if language.lower()=="python": result["validation"]=self.validate_code(code)
        return result

    def security_scan_code(self,code,language="Python",fix=False): return self.security.scan_code(code,language,fix)
    def security_scan_path(self,project_path,fix=False): return self.security.scan_path(project_path,fix)
    def security_assessment_url(self,target_url,headers=None): return {"static":{"status":"not_applicable","findings":[],"summary":{"critical":0,"high":0,"medium":0,"low":0}},"dynamic":self.dast.scan_url(target_url,explicit=True,headers=headers),"code":None,"fixed":False,"target":target_url}
    def security_assessment_code(self,code,language="Python",fix=False):
        static=self.security.scan_code(code,language,fix); final_code=static.get("fixed_code",code) if fix else code; dynamic=self.dast.scan_code(final_code,language); result={"static":static,"dynamic":dynamic,"code":final_code,"fixed":bool(fix and static.get("fixed_code"))}
        if fix and final_code!=code: result["post_static"]=self.security.scan_code(final_code,language,False)
        return result
    def security_assessment_path(self,project_path,fix=False):
        static=self.security.scan_path(project_path,fix); dynamic=self.dast.scan_path(project_path); return {"static":static,"dynamic":dynamic,"fixed":bool(fix and static.get("fixed"))}
    def latest_generated_project(self):
        rows=fetch_all("SELECT * FROM generated_projects ORDER BY id DESC LIMIT 1"); return rows[0] if rows else None
    def security_scan_latest_generated(self,fix=False):
        project=self.latest_generated_project()
        if not project:return {"status":"no_project","message":"No generated project is available for security testing."}
        result=self.security_assessment_code(project["code"],project["language"],fix)
        if fix and result.get("code") and result["code"]!=project["code"]: execute("UPDATE generated_projects SET code=? WHERE id=?",(result["code"],project["id"]))
        result["project_id"]=project["id"]; result["request"]=project["request"]; return result
    def validate_code(self,code):
        r=run_python(code); p=r.return_code==0 and not r.timed_out; execute("INSERT INTO experiments(language,code,output,error,passed) VALUES(?,?,?,?,?)",("Python",code,r.output,r.error,int(p))); return {"passed":p,"output":r.output,"error":r.error,"return_code":r.return_code,"timed_out":r.timed_out}
    @staticmethod
    def _half_percent(value): return max(0.0,min(100.0,round(float(value)*2)/2))

    def detailed_status(self,language=None):
        """Return every incomplete curriculum or persisted learning topic."""
        rows=fetch_all(
            "SELECT id,language,topic,status,score,progress_percent,phase,created_at FROM learning_sessions ORDER BY id DESC"
        )
        selected = [canonical_language(language)] if language else list(dict.fromkeys(
            list(LANGUAGE_CURRICULA.keys()) +
            [str(r["language"]) for r in rows if str(r["language"]).strip()]
        ))
        courses=[]
        for lang in selected:
            lang_rows=[r for r in rows if str(r["language"])==lang]
            latest={}
            for row in lang_rows:
                name=str(row["topic"]).strip()
                if not name or name in latest:
                    continue
                latest[name]=row

            curriculum_topics=LANGUAGE_CURRICULA.get(lang,[])
            topic_defs=[dict(item) for item in curriculum_topics]
            known={str(item.get("topic") or "").strip() for item in topic_defs}
            next_order=max([int(item.get("order") or 0) for item in topic_defs] or [0])+1

            # Persisted learning sessions are authoritative for ad-hoc topics too.
            # This prevents topics such as Cisco from disappearing merely because
            # they are not part of the fixed curriculum.
            for row in lang_rows:
                name=str(row["topic"]).strip()
                if not name or name in known:
                    continue
                topic_defs.append({
                    "order":next_order,
                    "topic":name,
                    "goal":f"Learning track for {lang}",
                })
                known.add(name)
                next_order += 1

            topic_items=[]
            all_progress=[]
            completed=0
            for item in topic_defs:
                name=str(item.get("topic") or "").strip()
                row=latest.get(name)
                progress=100.0 if row and row["status"]=="completed" else (
                    float(row["progress_percent"] or 0) if row else 0.0
                )
                progress=self._half_percent(progress)
                all_progress.append(progress)
                if progress >= 100.0:
                    completed += 1
                    continue
                topic_items.append({
                    "order":item.get("order"),
                    "topic":name,
                    "goal":item.get("goal",""),
                    "status":str(row["status"]) if row else "planned",
                    "phase":str(row["phase"]) if row else "planned",
                    "progress_percent":progress,
                    "score":row["score"] if row and row["score"] is not None else None,
                    "updated_at":row["created_at"] if row else None,
                })

            if not topic_items:
                continue

            overall=self._half_percent(sum(all_progress)/len(all_progress)) if all_progress else 0.0
            active=next((x for x in topic_items if x["status"]!="paused"),topic_items[0])
            courses.append({
                "language":lang,
                "total_topics":len(topic_defs),
                "completed_topics":completed,
                "remaining_topics":len(topic_items),
                "progress_percent":overall,
                "current":active,
                "topics":topic_items,
            })
        return {"courses":courses}

    def status(self,language=None):
        rows=fetch_all(
            "SELECT id,language,topic,status,score,progress_percent,phase,created_at FROM learning_sessions ORDER BY id DESC"
        ); out=[]
        for lang,topics in LANGUAGE_CURRICULA.items():
            topic_names={str(x["topic"]) for x in topics}
            lang_rows=[r for r in rows if r["language"]==lang and str(r["topic"]) in topic_names]
            completed_topics={str(r["topic"]) for r in lang_rows if r["status"]=="completed"}
            completed=len(completed_topics); total=len(topics)
            active_progress=max([float(r["progress_percent"] or 0) if "progress_percent" in r.keys() and r["progress_percent"] is not None else 0.0 for r in lang_rows if r["status"]!="completed"] or [0.0])
            raw=((completed + active_progress/100.0) / total * 100.0) if total else 0.0
            scores=[float(r["score"]) for r in lang_rows if r["status"]=="completed" and r["score"] is not None]
            out.append({"language":lang,"completed_topics":completed,"remaining_topics":max(0, total - completed),"total_topics":total,"progress_percent":self._half_percent(raw),"progress_step":"0.5%","average_score":round(sum(scores)/len(scores),1) if scores else 0})
        if language: out=[x for x in out if x["language"].lower()==canonical_language(language).lower()]
        session_fields=("id","language","topic","status","score","progress_percent","phase","created_at")
        sessions=[{key: row[key] for key in session_fields if key in row.keys()} for row in rows]
        return {"languages":out,"sessions":sessions,"available_languages":list(LANGUAGE_CURRICULA.keys())}
