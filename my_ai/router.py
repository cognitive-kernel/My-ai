from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Intent:
    name: str
    confidence: float
    requires_confirmation: bool = False


HIGH_RISK = {"pentest_external","git_write","self_update","database_import","code_execution"}


def classify(text: str) -> Intent:
    low = re.sub(r"\s+", " ", text.lower()).strip()
    patterns = [
        ("self_update", ("self-update","بروزرسانی خودت","آپدیت خودت"), 0.99),
        ("git_write", ("github بنویس","git write","فایل را در گیت","روی گیت تغییر بده"), 0.96),
        ("pentest_external", ("پن‌تست آدرس:","pentest http://","pentest https://"), 0.95),
        ("learning", ("یاد بگیر","یادگیری","learn","study"), 0.92),
        ("code_execution", ("کد را اجرا کن","اجرا کن","run this code"), 0.9),
        ("coding", ("کد بنویس","برنامه بنویس","write code","build"), 0.86),
        ("chat", tuple(), 0.5),
    ]
    for name, words, confidence in patterns:
        if words and any(w in low for w in words):
            return Intent(name, confidence, name in HIGH_RISK)
    return Intent("chat", 0.5, False)
