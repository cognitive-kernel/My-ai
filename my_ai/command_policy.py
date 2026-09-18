from __future__ import annotations
from dataclasses import dataclass

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
LEARN_WORDS=("یاد بگیر","یادگیری","یاد بگیر که","learn","study","go learn")
BUILD_WORDS=("بساز","بنویس","برنامه بنویس","پروژه بساز","ایجاد کن","create","build","write","make")

def parse_command(text: str) -> CommandPolicy:
    low=text.lower()
    security=any(x in low for x in SEC_WORDS)
    report=any(x in low for x in REPORT_WORDS)
    fix=any(x in low for x in FIX_WORDS)
    # Explicit user instruction always overrides the default.
    if report:
        action="report"
    elif fix:
        action="fix"
    elif security:
        action="fix"  # My-AI default for an explicit pentest request.
    else:
        action="default"
    learn=any(x in low for x in LEARN_WORDS)
    build=any(x in low for x in BUILD_WORDS)
    return CommandPolicy(security=security,security_action=action,learn=learn,build=build)
