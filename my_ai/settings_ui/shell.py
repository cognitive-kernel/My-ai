from html import escape

def shell(title: str, body: str, script: str = "") -> str:
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} | My-AI</title>
<style>
body{{font-family:Tahoma,system-ui;background:#f5f7fb;color:#17202a;margin:0}}
main{{max-width:920px;margin:auto;padding:24px}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:18px;margin:12px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}}
label{{display:block;font-weight:700;margin:8px 0}}
input,select,textarea{{width:100%;box-sizing:border-box;padding:9px;border:1px solid #cbd5e1;border-radius:8px}}
button,a.button{{display:inline-block;border:0;border-radius:8px;padding:9px 14px;background:#1d4ed8;color:#fff;text-decoration:none;cursor:pointer;margin:4px 0}}
.muted{{color:#64748b}}
pre{{white-space:pre-wrap;overflow:auto;background:#f8fafc;padding:10px;border-radius:8px}}
</style></head><body><main>
<p><a href="/settings">تنظیمات</a> · <a href="/">صفحه اصلی</a></p>
{body}
</main><script>{script}</script></body></html>"""
