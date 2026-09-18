from __future__ import annotations
import threading
from .learner import LearningEngine
class StudyScheduler:
    def __init__(self,interval_seconds=3600):
        self.interval_seconds=interval_seconds; self._stop=threading.Event(); self._thread=None; self.language="Python"; self.last_result=None
    def start(self,language="Python"):
        if self._thread and self._thread.is_alive(): return
        self.language=language; self._stop.clear(); self._thread=threading.Thread(target=self._loop,args=(language,),daemon=True); self._thread.start()
    def stop(self): self._stop.set()
    def running(self): return bool(self._thread and self._thread.is_alive())
    def _loop(self,language):
        engine=LearningEngine()
        while not self._stop.is_set():
            try: self.last_result=engine.learn_next(language)
            except Exception as exc: self.last_result={"status":"error","error":str(exc)}
            if self.last_result and self.last_result.get("status")=="completed" and self.last_result.get("message","").endswith("complete."): break
            self._stop.wait(self.interval_seconds)
