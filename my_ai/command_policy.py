from __future__ import annotations
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class CommandPolicy:
    language: str | None = None
    security: bool = False
    security_action: str = "default"
    learn: bool = False
    build: bool = False

REPORT_WORDS=("فقط گزارش","فقط بگو","فقط لیست","گزارش بده","گزارش کن","اشکالات را بگو","اشکالات رو بگو","فقط تست بگیر","فقط بررسی کن","only report","report only","just report","list findings")
FIX_WORDS=("رفع کن","رفعش کن","برطرف کن","اصلاح کن","درستش کن","رفع باگ","باگ‌ها را رفع","باگها را رفع","fix","fix them","remediate","repair")
SEC_WORDS=("پن تست","پنتست","تست نفوذ","تست امنیت","pentest","pen test","penetration test","security test")
TEST_WORDS=("تست بگیر","بررسی امنیتی","امنیتش را بررسی","security check","security scan")
LEARN_WORDS=("یاد بگیر","یادگیری","یاد بگیر که","learn","study","go learn")
BUILD_WORDS=("بساز","بنویس","برنامه بنویس","پروژه بساز","ایجاد کن","create","build","write","make")

def _contains(text, words):
    return any((re.search(r"(?<![A-Za-z])"+re.escape(x)+r"(?![A-Za-z])",text) if x.isascii() else x in text) for x in words)

def parse_command(text: str) -> CommandPolicy:
    low=re.sub(r"\s+"," ",text.lower()).strip()
    security=_contains(low,SEC_WORDS) or _contains(low,TEST_WORDS)
    report=_contains(low,REPORT_WORDS)
    explicit_negated_fix=bool(re.search(r"(do not|don't|don’t|without|never|not)\s+(fix|remediate|repair)|نباید\s+.*(رفع|اصلاح|درست)",low))
    fix=_contains(low,FIX_WORDS) and not explicit_negated_fix
    if report:
        action="report"
    elif fix:
        action="fix"
    elif security:
        action="report"
    else:
        action="default"
    return CommandPolicy(security=security,security_action=action,learn=_contains(low,LEARN_WORDS),build=_contains(low,BUILD_WORDS))
