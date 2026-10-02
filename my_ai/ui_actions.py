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
    UIAction("control-plane.list", "control-plane", "نمایش Control Plane", "نمایش تمام رکوردهای مدیریت بدون کدنویسی.", "GET", "/settings/control-plane", "settings:read"),
    UIAction("control-plane.actions", "control-plane", "تاریخچه عملیات", "نمایش وضعیت عملیات GUI/CLI.", "GET", "/settings/control-plane/actions", "settings:read"),
    UIAction("metrics.snapshot", "observability", "مشاهده Metrics", "مشاهده مصرف مدل، latency، خطا و routing.", "GET", "/settings/metrics", "observability:read"),
    UIAction("learning.sources", "learning", "مدیریت منابع یادگیری", "نمایش منابع، provenance و وضعیت approval.", "GET", "/settings/learning-sources", "learning:read"),
    UIAction("profiles.list", "configuration", "مدیریت پروفایل‌ها", "نمایش پروفایل‌های پیکربندی.", "GET", "/settings/profiles", "settings:read"),
    UIAction("capabilities.list", "configuration", "فهرست قابلیت‌ها", "نمایش قابلیت‌های قابل مدیریت بدون کدنویسی.", "GET", "/settings/capabilities", "settings:read"),
    UIAction("config.history", "configuration", "تاریخچه تنظیمات", "نمایش تغییرات ثبت‌شده در Configuration Registry.", "GET", "/settings/registry/history", "settings:read"),
    UIAction("provider.catalog", "llm", "کاتالوگ Provider و Model", "نمایش Providerها و Modelهای قابل مدیریت.", "GET", "/settings/providers", "models:read"),
    UIAction("learning.catalog", "learning", "کاتالوگ آموزش", "نمایش مسیرها و منابع یادگیری.", "GET", "/learning/catalog", "learning:read"),
    UIAction("profiles.catalog", "configuration", "پروفایل‌های تنظیمات", "نمایش پروفایل‌های ذخیره‌شده.", "GET", "/settings/profiles", "settings:read"),
    UIAction("database.backup.policy", "database", "وضعیت Backup", "نمایش سیاست‌های Backup و Database.", "GET", "/settings/control-plane?namespace=database.backup", "database:read"),
    UIAction("security.roles", "security", "مدیریت Security Policy", "نمایش رکوردهای نقش، قابلیت و کنترل دسترسی.", "GET", "/settings/control-plane?namespace=security.roles", "security:read"),
    UIAction("evaluation.regression", "evaluation", "Regression Intelligence", "نمایش تنظیمات ارزیابی و regression.", "GET", "/settings/control-plane?namespace=evaluation.regression", "eval:read"),

    UIAction("github.check", "github", "بررسی اتصال GitHub", "وضعیت اتصال GitHub را بررسی می‌کند.", "GET", "/git/check", "github:read"),
    UIAction("image.health", "image", "بررسی موتور تصویر", "وضعیت موتور تصویر محلی را بررسی می‌کند.", "GET", "/settings/image/status", "tools:read"),
    UIAction("scheduler.status", "scheduler", "بررسی زمان‌بندی", "وضعیت scheduler و workerها را نمایش می‌دهد.", "GET", "/scheduler/status", "scheduler:read"),
    UIAction("self-repair.status", "self-repair", "بررسی Self-Repair", "وضعیت و آخرین proposalهای تعمیر را بررسی می‌کند.", "GET", "/self-repair/status", "self-repair:read"),
)


def list_ui_actions() -> list[dict]:
    return [asdict(action) for action in _ACTIONS]
