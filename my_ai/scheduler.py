from __future__ import annotations
import threading
from .learner import LearningEngine
class StudyScheduler:
    def __init__(self,interval_seconds=3600):
        self.interval_seconds=interval_seconds; self._stop=threading.Event(); self._thread=None
    def start(self,language="Python"):
        if self._thread and self._thread.is_alive(): return
        self._stop.clear(); self._thread=threading.Thread(target=self._loop,args=(language,),daemon=True); self._thread.start()
    def stop(self): self._stop.set()
    def _loop(self,language):
        engine=LearningEngine()
        while not self._stop.is_set():
            try: engine.autonomous_step(language)
            except Exception: pass
            self._stop.wait(self.interval_seconds)
