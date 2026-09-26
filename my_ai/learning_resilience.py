from __future__ import annotations

import time

from .config import settings
from .learner import LearningEngine
from .settings_store import get_int


def retry_forever(self, operation, label, progress_callback=None, topic=None, stop_event=None):
    """Retry a learning operation with exponential backoff and the configured retry limit.

    The historical method name is kept for compatibility, but a permanent source/LLM
    failure must not block the learning worker forever. Cancellation is checked before
    every attempt and while waiting between attempts.
    """
    delay = 1.0
    max_attempts = max(1, get_int("learning.max_retries", settings.learning_max_retries))
    for attempt in range(1, max_attempts + 1):
        if stop_event is not None and stop_event.is_set():
            raise InterruptedError("learning stopped")
        try:
            return operation()
        except Exception as exc:
            if stop_event is not None and stop_event.is_set():
                raise InterruptedError("learning stopped") from exc
            if attempt >= max_attempts:
                raise RuntimeError(
                    f"{label} failed after {max_attempts} attempts: {exc}"
                ) from exc
            if progress_callback:
                progress_callback("retrying", topic or label)
            if stop_event is None:
                time.sleep(delay)
            else:
                stop_event.wait(delay)
            delay = min(delay * 2.0, 60.0)

    raise RuntimeError(f"{label} failed")


def install() -> None:
    # Keep the explicit bounded retry implementation intact. Only the legacy
    # alias is installed so startup cannot accidentally turn bounded retries
    # into an infinite loop.
    setattr(LearningEngine, "_retry_forever", retry_forever)
