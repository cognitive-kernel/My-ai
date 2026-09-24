from __future__ import annotations

import time


def install() -> None:
    from . import settings_feature as sf

    if getattr(sf, "_myai_resilience_installed", False):
        return

    def resilient_run_course(course_id: int) -> None:
        if course_id in sf._running:
            return
        sf._running.add(course_id)
        delay = 1.0
        first_iteration = True
        try:
            while True:
                course = sf._course(course_id)
                if not course or not course["active"]:
                    return
                rows = sf._progress(course_id)
                topic = next((x for x in rows if x["status"] != "completed"), None)
                if not topic:
                    return
                # On a new /start invocation, a paused topic is the resume target.
                # During an already-running worker, a paused topic is a durable stop.
                if topic["status"] == "paused" and not first_iteration:
                    return
                first_iteration = False
                try:
                    sf._learn_topic(course_id, topic)
                    delay = 1.0
                except Exception as exc:
                    current = sf._progress(course_id)
                    current_topic = next((x for x in current if int(x["id"]) == int(topic["id"])), None)
                    if current_topic and current_topic["status"] == "paused":
                        return
                    sf._set_topic(
                        int(topic["id"]),
                        "retrying",
                        float(topic["progress_percent"]),
                        "retrying",
                        lesson=f"Learning error; retrying automatically: {exc}",
                    )
                    time.sleep(delay)
                    delay = min(delay * 2.0, 60.0)
                    continue
                remaining = sf.fetch_all(
                    "SELECT id FROM custom_course_topics t WHERE t.course_id=? AND NOT EXISTS "
                    "(SELECT 1 FROM custom_course_progress p WHERE p.topic_id=t.id AND p.status='completed')",
                    (course_id,),
                )
                if not remaining:
                    return
        finally:
            sf._running.discard(course_id)

    sf._run_course = resilient_run_course
    sf._myai_resilience_installed = True
