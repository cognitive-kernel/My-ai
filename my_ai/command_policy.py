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
# These phrases request source/project generation, not execution of a build toolchain.
# Actual build/compile/run remains a separately confirmable high-risk operation.
BUILD_WORDS=(
    "پروژه بساز","پروژه ایجاد کن","ایجاد پروژه","اپلیکیشن بساز","برنامه بساز",
    "build project","create project","create application","build application","make a project",
    "compile the project","build the application",
)
# Source/file generation phrases (indicator, single file) — NOT application toolchain build.
GENERATE_FILE_WORDS=("بساز","فایل بساز","همونو بساز","همان را بساز","همون فایل رو بساز","create file","write file")
INDICATOR_WORDS=("اندیکاتور","indicator","mql4","mql5","mq4","mq5","متاتریدر","metatrader","اکسپرت","expert advisor")

def _contains(text, words):
    return any((re.search(r"(?<![A-Za-z])"+re.escape(x)+r"(?![A-Za-z])",text) if x.isascii() else x in text) for x in words)

LANGUAGE_ALIASES={
    "python":"Python","py":"Python","پایتون":"Python",
    "javascript":"JavaScript","js":"JavaScript","جاوااسکریپت":"JavaScript",
    "typescript":"TypeScript","ts":"TypeScript",
    "java":"Java","go":"Go","golang":"Go","rust":"Rust",
    "c++":"C++","cpp":"C++","c#":"C#","csharp":"C#",
    "php":"PHP","ruby":"Ruby","sql":"SQL","bash":"Bash","shell":"Bash",
    "mql4":"MQL4","mql 4":"MQL4","mq4":"MQL4","mql":"MQL4","متا تریدر 4":"MQL4","متاتریدر 4":"MQL4","metatrader 4":"MQL4","metatrader":"MQL4",
}

def _detect_language(text):
    for alias,canonical in sorted(LANGUAGE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias.isascii():
            if re.search(r"(?<![A-Za-z0-9_+#])"+re.escape(alias)+r"(?![A-Za-z0-9_+#])", text, re.IGNORECASE):
                return canonical
        elif alias in text:
            return canonical
    return None

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
    build=_contains(low,BUILD_WORDS)
    # "بساز اندیکاتور/MQL" is source generation, not project toolchain build
    if _contains(low, INDICATOR_WORDS) or (
        _contains(low, GENERATE_FILE_WORDS) and _contains(low, INDICATOR_WORDS)
    ):
        build = False
    elif _contains(low, INDICATOR_WORDS):
        build = False
    return CommandPolicy(language=_detect_language(low),security=security,security_action=action,learn=_contains(low,LEARN_WORDS),build=build)
