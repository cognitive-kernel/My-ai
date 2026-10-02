from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
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
) -> list[ParallelResult]:
    if max_workers < 1:
        raise ValueError("max_workers must be >= 1")
    values = list(items)
    results: list[ParallelResult] = [ParallelResult(i) for i in range(len(values))]
    with ThreadPoolExecutor(max_workers=min(max_workers, max(1, len(values)))) as pool:
        futures: dict[Future[R], int] = {pool.submit(fn, item): i for i, item in enumerate(values)}
        for future, index in ((f, i) for f, i in futures.items()):
            try:
                results[index] = ParallelResult(index, value=future.result())
            except BaseException as exc:
                results[index] = ParallelResult(index, error=exc)
    return results
