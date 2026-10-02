from __future__ import annotations

import json
import logging
import subprocess
import sys
import tempfile
import shutil
import uuid
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .db import execute
from .settings_store import get_bool
from .llm import create_llm
from .self_update import recent_lessons
from .decision_log import record as record_decision
from .access_policy import assert_mutation_allowed
from .notifications import notify
from .state_backup import database_snapshot, restore_database_snapshot

ROOT = Path(__file__).resolve().parent.parent
PROPOSALS = ROOT / "self-repair" / "proposals"
logger = logging.getLogger(__name__)

def _run(args, cwd: Path, timeout: int): return subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)
def _git(*args: str, cwd: Path = ROOT, timeout: int = 120): return _run(["git", *args], cwd, timeout)

def _tests(cwd: Path):
    compile_run=_run([sys.executable,"-m","compileall","-q","my_ai"],cwd,120)
    if compile_run.returncode: return False,"compileall failed:\n"+(compile_run.stdout+compile_run.stderr).strip()
    test_run=_run([sys.executable,"-m","pytest","-q"],cwd,300)
    if test_run.returncode: return False,"pytest failed:\n"+(test_run.stdout+test_run.stderr).strip()
    return True,"compileall + pytest passed"

def _clean_git(): return not bool(_git("status","--porcelain").stdout.strip())

def diagnose_local():
    head=_git("rev-parse","HEAD"); status=_git("status","--short"); tests_ok,tests=_tests(ROOT); lessons=recent_lessons(20)
    result={"timestamp":datetime.now(timezone.utc).isoformat(),"head":head.stdout.strip(),"clean":not bool(status.stdout.strip()),"status":status.stdout,"tests_passed":tests_ok,"tests":tests,"lessons":lessons}
    execute("INSERT INTO fix_attempts(event,patch,test_result,activated) VALUES(?,?,?,?)",("repair_diagnosis",None,tests,0)); return result

def _normalize_patch(raw: str):
    patch=raw.strip(); fence=chr(96)*3
    if patch.startswith(fence):
        patch=patch[len(fence):].lstrip(); patch=patch.split("\n",1)[1].lstrip() if not patch.startswith("diff") and "\n" in patch else patch
        if patch.endswith(fence): patch=patch[:-len(fence)].rstrip()
    if "diff --git " not in patch: raise ValueError("The model did not return a unified git patch.")
    return patch+"\n"

def _test_patch(patch: str, base: str):
    parent=Path(tempfile.mkdtemp(prefix="myai-repair-")); candidate=parent/"worktree"
    try:
        add=_git("worktree","add","--detach",str(candidate),base,timeout=120)
        if add.returncode: return False,"worktree creation failed:\n"+(add.stdout+add.stderr).strip()
        patch_file=candidate/".myai-repair.patch"; patch_file.write_text(patch,encoding="utf-8")
        check=_git("apply","--check",str(patch_file),cwd=candidate)
        if check.returncode: return False,"git apply --check failed:\n"+(check.stdout+check.stderr).strip()
        apply=_git("apply","--index",str(patch_file),cwd=candidate)
        if apply.returncode: return False,"git apply failed:\n"+(apply.stdout+apply.stderr).strip()
        return _tests(candidate)
    finally:
        _git("worktree","remove","--force",str(candidate),timeout=120); shutil.rmtree(parent,ignore_errors=True)

def propose_repair(issue: str):
    assert_mutation_allowed("self-repair proposal")
    if not get_bool("self_repair.enabled",True): raise ValueError("Self-repair is disabled in Settings.")
    if not issue.strip(): raise ValueError("A concrete local bug description is required.")
    diagnosis=diagnose_local(); base=str(diagnosis["head"]); prompt=("You are the My-AI senior repair engineer. Diagnose the supplied local failure and propose the smallest safe source patch. Return ONLY a valid unified git diff beginning with 'diff --git'.\n\nISSUE:\n"+issue+"\n\nDIAGNOSIS:\n"+json.dumps(diagnosis,ensure_ascii=False,indent=2)+"\n\nRECENT LESSONS:\n"+json.dumps(recent_lessons(20),ensure_ascii=False,indent=2))
    llm=create_llm("coding"); raw=""; patch=""; passed=False; test_result=""; last_error=""
    for _ in range(3):
        raw=llm.chat(prompt+(("\n\nPREVIOUS OUTPUT WAS INVALID. REPAIR IT:\n"+last_error) if last_error else ""),system="You generate minimal, testable git patches. Never return prose.")
        try: patch=_normalize_patch(raw)
        except ValueError as exc: last_error=str(exc)+"\nOUTPUT:\n"+raw[:12000]; continue
        passed,test_result=_test_patch(patch,base); break
    if not patch: raise ValueError("The model failed to produce a valid unified git patch after 3 attempts.")
    proposal_id=uuid.uuid4().hex; PROPOSALS.mkdir(parents=True,exist_ok=True); proposal={"id":proposal_id,"created_at":datetime.now(timezone.utc).isoformat(),"base":base,"issue":issue,"patch":patch,"isolated_tests_passed":passed,"test_result":test_result,"approved":False,"applied":False}
    (PROPOSALS/f"{proposal_id}.json").write_text(json.dumps(proposal,ensure_ascii=False,indent=2),encoding="utf-8"); execute("INSERT INTO fix_attempts(event,patch,test_result,activated) VALUES(?,?,?,?)",("repair_proposal",patch,test_result,0)); record_decision("self_repair_proposal","propose",{"proposal_id":proposal_id,"isolated_tests_passed":passed}); return proposal

def apply_repair(proposal_id: str, approved: bool, health_url: str | None = None, health_timeout: float = 20.0):
    assert_mutation_allowed("self-repair apply")
    if not get_bool("self_repair.enabled",True): raise ValueError("Self-repair is disabled in Settings.")
    if get_bool("self_repair.require_approval",True) and not approved: raise ValueError("Explicit approval is required before applying a repair.")
    path=PROPOSALS/f"{proposal_id}.json"
    if not path.is_file(): raise ValueError("Repair proposal not found.")
    proposal=json.loads(path.read_text(encoding="utf-8"))
    if not proposal.get("isolated_tests_passed"): raise ValueError("Only a repair proposal that passed isolated tests can be applied.")
    current=_git("rev-parse","HEAD").stdout.strip()
    if current!=proposal["base"]: raise ValueError("Repository HEAD changed since the proposal was generated; regenerate the repair.")
    if not _clean_git(): raise ValueError("Working tree must be clean before applying a repair.")
    snapshot_path=PROPOSALS/f"{proposal_id}.db.sqlite"
    db_snapshot=database_snapshot(snapshot_path)
    proposal["snapshot"]=str(db_snapshot)
    path.write_text(json.dumps(proposal,ensure_ascii=False,indent=2),encoding="utf-8")
    patch_file=PROPOSALS/f"{proposal_id}.patch"; patch_file.write_text(str(proposal["patch"]),encoding="utf-8"); applied=_git("apply",str(patch_file))
    if applied.returncode: execute("INSERT INTO fix_attempts(event,patch,test_result,activated) VALUES(?,?,?,?)",("repair_apply_failed",proposal["patch"],applied.stderr or applied.stdout,0)); raise RuntimeError("Repair patch could not be applied:\n"+(applied.stderr or applied.stdout))
    ok,tests=_tests(ROOT)
    if not ok:
        _git("reset","--hard",proposal["base"])
        try: restore_database_snapshot(Path(db_snapshot))
        except Exception as restore_exc: _record_failure_lesson("self_repair_restore_failed",proposal_id,str(restore_exc))
        execute("INSERT INTO fix_attempts(event,patch,test_result,activated) VALUES(?,?,?,?)",("repair_rolled_back",proposal["patch"],tests,0)); raise RuntimeError("Applied repair failed post-apply tests and was rolled back:\n"+tests)
    if health_url:
        deadline=time.time()+max(1.0,float(health_timeout))
        healthy=False
        last_error=""
        while time.time()<deadline:
            try:
                with urllib.request.urlopen(health_url,timeout=3) as response:
                    healthy=int(response.status)==200
                    if healthy: break
            except Exception as exc:
                last_error=str(exc)
            time.sleep(0.5)
        if not healthy:
            _git("reset","--hard",proposal["base"])
            _record_failure_lesson("self_repair_health_failed",proposal_id,last_error)
            raise RuntimeError("Post-activation health check failed and repair was rolled back: "+last_error)
    proposal["approved"]=True; proposal["applied"]=True; proposal["applied_at"]=datetime.now(timezone.utc).isoformat(); path.write_text(json.dumps(proposal,ensure_ascii=False,indent=2),encoding="utf-8"); execute("INSERT INTO fix_attempts(event,patch,test_result,activated) VALUES(?,?,?,?)",("repair_applied",proposal["patch"],tests,1)); record_decision("self_repair","apply",{"proposal_id":proposal_id}); notify("self_repair_applied",{"proposal_id":proposal_id,"base":proposal["base"]}); return {"status":"applied","proposal_id":proposal_id,"base":proposal["base"],"tests":tests,"working_tree":"modified"}


def _record_failure_lesson(event: str, proposal_id: str, error: str) -> None:
    lesson = ROOT / "self-repair" / "lessons.jsonl"
    lesson.parent.mkdir(parents=True, exist_ok=True)
    item = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, "proposal_id": proposal_id, "error": str(error)[:4000]}
    with lesson.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    try:
        execute("INSERT INTO fix_attempts(event,patch,test_result,activated) VALUES(?,?,?,?)", (event, proposal_id, str(error)[:4000], 0))
    except Exception as exc:
        logger.warning("SELF_REPAIR_LESSON_PERSIST_FAILED: %s", exc)

def list_proposals():
    PROPOSALS.mkdir(parents=True,exist_ok=True); items=[]
    for path in sorted(PROPOSALS.glob("*.json"),key=lambda p:p.stat().st_mtime,reverse=True):
        try:
            item=json.loads(path.read_text(encoding="utf-8")); items.append({k:item.get(k) for k in ("id","created_at","base","issue","isolated_tests_passed","approved","applied")})
        except (OSError,UnicodeError,json.JSONDecodeError) as exc:
            logger.warning("SELF_REPAIR_PROPOSAL_READ_FAILED path=%s error=%s",path,exc)
    return items[:100]

def proposal_diff(proposal_id: str):
    proposal=proposal_status(proposal_id); return {"id":proposal_id,"base":proposal.get("base"),"issue":proposal.get("issue"),"diff":proposal.get("patch","")}

def proposal_status(proposal_id: str):
    path=PROPOSALS/f"{proposal_id}.json"
    if not path.is_file(): raise ValueError("Repair proposal not found.")
    return json.loads(path.read_text(encoding="utf-8"))
