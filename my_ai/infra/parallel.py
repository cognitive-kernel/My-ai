from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event

from .cancellation import CancellationToken
from dataclasses import dataclass
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")
R = TypeVar("R")


@dataclass(frozen=True)
class ParallelResult:
    index: int
    value: object | None = None
    error: BaseException | None = None


def map_independent(
    fn: Callable[[T], R],
    items: Iterable[T],
    *,
    max_workers: int = 4,
    cancel_event: Event | CancellationToken | None = None,
) -> list[ParallelResult]:
    if max_workers < 1:
        raise ValueError("max_workers must be >= 1")
    values = list(items)
    if cancel_event is not None and (cancel_event.is_cancelled if isinstance(cancel_event, CancellationToken) else cancel_event.is_set()):
        return [ParallelResult(i, error=RuntimeError("parallel execution cancelled")) for i in range(len(values))]
    results: list[ParallelResult] = [ParallelResult(i) for i in range(len(values))]
    with ThreadPoolExecutor(max_workers=min(max_workers, max(1, len(values)))) as pool:
        futures: dict[Future[R], int] = {pool.submit(fn, item): i for i, item in enumerate(values)}
        for future, index in ((f, i) for f, i in futures.items()):
            if cancel_event is not None and (cancel_event.is_cancelled if isinstance(cancel_event, CancellationToken) else cancel_event.is_set()) and not future.done():
                future.cancel()
            if future.cancelled():
                results[index] = ParallelResult(index, error=RuntimeError("parallel execution cancelled"))
                continue
            try:
                results[index] = ParallelResult(index, value=future.result())
            except BaseException as exc:
                results[index] = ParallelResult(index, error=exc)
    return results
