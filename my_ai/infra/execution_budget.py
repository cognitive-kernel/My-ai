from __future__ import annotations

from dataclasses import dataclass
import time


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class ExecutionBudget:
    max_steps: int | None = None
    max_tool_calls: int | None = None
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    max_seconds: float | None = None
    steps: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    started_at: float = 0.0

    def __post_init__(self) -> None:
        self.started_at = time.monotonic()

    def _check(self, current: int, limit: int | None, label: str) -> None:
        if limit is not None and current > limit:
            raise BudgetExceeded(f"{label} budget exceeded")

    def step(self) -> None:
        self.steps += 1
        self._check(self.steps, self.max_steps, "step")
        self.check_time()

    def tool_call(self) -> None:
        self.tool_calls += 1
        self._check(self.tool_calls, self.max_tool_calls, "tool")
        self.check_time()

    def tokens(self, *, input_tokens: int = 0, output_tokens: int = 0) -> None:
        self.input_tokens += max(0, int(input_tokens))
        self.output_tokens += max(0, int(output_tokens))
        self._check(self.input_tokens, self.max_input_tokens, "input token")
        self._check(self.output_tokens, self.max_output_tokens, "output token")
        self.check_time()

    def check_time(self) -> None:
        if self.max_seconds is not None and time.monotonic() - self.started_at > self.max_seconds:
            raise BudgetExceeded("time budget exceeded")

    @property
    def remaining_seconds(self) -> float | None:
        if self.max_seconds is None:
            return None
        return max(0.0, self.max_seconds - (time.monotonic() - self.started_at))
