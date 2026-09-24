from __future__ import annotations

import time

from .learner import LearningEngine


def retry_forever(self, operation, label, progress_callback=None, topic=None, stop_event=None):
    delay = 1.0
    while True:
        if stop_event is not None and stop_event.is_set():
            raise InterruptedError("learning stopped")
        try:
            return operation()
        except Exception as exc:
            if stop_event is not None and stop_event.is_set():
                raise InterruptedError("learning stopped") from exc
            if progress_callback:
                progress_callback("retrying", topic or label)
            if stop_event is None:
                time.sleep(delay)
            else:
                stop_event.wait(delay)
            delay = min(delay * 2.0, 60.0)


def install() -> None:
    setattr(LearningEngine, "_retry_with_limit", retry_forever)
    setattr(LearningEngine, "_retry_forever", retry_forever)
