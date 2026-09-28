"""Run from project root:  .venv\\Scripts\\python.exe patch_api_chat_guard.py"""
from pathlib import Path

path = Path("my_ai/api.py")
text = path.read_text(encoding="utf-8")
if "never hard-stop indicator/code file requests" in text:
    print("already patched")
    raise SystemExit(0)

guard_block = '''        intent=classify(msg)
        # Guard: never hard-stop indicator/code file requests as database_import
        if intent.name == "database_import":
            _m = (
                "اندیکاتور", "indicator", "mql4", "mql5", "mq4", "mq5",
                "متاتریدر", "metatrader", ".mq4", ".mq5", "اکسپرت",
            )
            if any(t in low for t in _m) or (
                any(t in low for t in ("بساز", "بنویس", "دانلود", "ذخیره", "لینک", "download", "save"))
                and any(t in low for t in ("فایل", "file", "کد", "code", "اندیکاتور", "indicator", "mql"))
            ):
                from .domain.router import Intent as DomainIntent
                intent = DomainIntent(
                    name="coding",
                    confidence=float(getattr(intent, "confidence", 0.5) or 0.5),
                    requires_confirmation=False,
                    args=dict(getattr(intent, "args", {}) or {}),
                    intents=("coding",),
                )
'''

# Unique context from chat() endpoint
old = (
    "        intent=classify(msg)\n"
    "        # Learning and image generation have dedicated pages/endpoints. Never execute\n"
)
if old not in text:
    old = "        intent=classify(msg)\n        # Learning and image generation have dedicated pages/endpoints."
    if old not in text:
        raise SystemExit("Patch site not found in my_ai/api.py")

new = guard_block + "        # Learning and image generation have dedicated pages/endpoints. Never execute\n"
# if old already includes Never execute line partially
if "Never execute\n" in old:
    text = text.replace(old, new, 1)
else:
    text = text.replace(
        "        intent=classify(msg)\n        # Learning and image generation have dedicated pages/endpoints.",
        guard_block + "        # Learning and image generation have dedicated pages/endpoints.",
        1,
    )
path.write_text(text, encoding="utf-8")
print("patched", path.resolve())
