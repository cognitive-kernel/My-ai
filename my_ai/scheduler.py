from __future__ import annotations
import threading
from .learner import LearningEngine

class StudyScheduler:
    def __init__(self,interval_seconds=3600):
        self.interval_seconds=interval_seconds
        self._stop=threading.Event()
        self._thread=None
        self.language="Python"
        self.last_result=None
        self.current_topic=None
        self.stage="idle"
        self.error=None
        self._lock=threading.Lock()

    def start(self,language="Python"):
        if self._thread and self._thread.is_alive(): return
        self.language=language
        self.last_result=None
        self.error=None
        self.stage="starting"
        self._stop.clear()
        self._thread=threading.Thread(target=self._loop,args=(language,),daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self.stage="stopping"

    def running(self):
        return bool(self._thread and self._thread.is_alive())

    def update_progress(self,stage,topic=None):
        with self._lock:
            self.stage=stage
            if topic: self.current_topic=topic

    def _loop(self,language):
        engine=LearningEngine()
        while not self._stop.is_set():
            try:
                self.update_progress("starting")
                self.last_result=engine.learn_next(language, progress_callback=self.update_progress)
                if self.last_result.get("status")=="completed":
                    self.update_progress("completed",self.last_result.get("topic",{}).get("topic"))
                elif self.last_result.get("status")=="complete":
                    self.update_progress("completed")
                    break
            except Exception as exc:
                self.error=str(exc)
                self.last_result={"status":"error","error":str(exc)}
                self.update_progress("error")
            if self.last_result and self.last_result.get("message","").endswith("complete."): break
            self._stop.wait(self.interval_seconds)

    def status(self):
        with self._lock:
            return {
                "running":self.running(),
                "language":self.language,
                "current_topic":self.current_topic,
                "stage":self.stage,
                "error":self.error,
                "last_result":self.last_result,
            }
