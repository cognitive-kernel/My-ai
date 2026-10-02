from __future__ import annotations

from threading import Event


class CancellationToken:
    """Cooperative cancellation primitive shared by long-running runtimes."""

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout)

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise InterruptedError("operation cancelled")

    @property
    def event(self) -> Event:
        return self._event
