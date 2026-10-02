from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


@dataclass(frozen=True)
class UIAction:
    id: str
    module: str
    label: str
    description: str
    method: Literal["GET", "POST"]
    endpoint: str
    permission: str
    confirmation: bool = False


_ACTIONS = (
    UIAction("github.check", "github", "بررسی اتصال GitHub", "وضعیت اتصال GitHub را بررسی می‌کند.", "GET", "/git/check", "github:read"),
    UIAction("image.health", "image", "بررسی موتور تصویر", "وضعیت موتور تصویر محلی را بررسی می‌کند.", "GET", "/settings/image/status", "tools:read"),
    UIAction("scheduler.status", "scheduler", "بررسی زمان‌بندی", "وضعیت scheduler و workerها را نمایش می‌دهد.", "GET", "/scheduler/status", "scheduler:read"),
    UIAction("self-repair.status", "self-repair", "بررسی Self-Repair", "وضعیت و آخرین proposalهای تعمیر را بررسی می‌کند.", "GET", "/self-repair/status", "self-repair:read"),
)


def list_ui_actions() -> list[dict]:
    return [asdict(action) for action in _ACTIONS]
