from __future__ import annotations

from fastapi.responses import HTMLResponse


INJECT = """
<div class="card" id="localFileTools" style="margin-top:12px">
  <b>فایل و پردازش محلی</b>
  <input id="chatFile" type="file" style="display:block;margin:8px 0" />
  <span class="small">فایل انتخاب‌شده در فضای محلی برنامه ذخیره و برای تحلیل به My-AI داده می‌شود.</span>
  <div style="margin-top:8px">
    <input id="fileGeneratePrompt" placeholder="برای ساخت فایل، توضیح کوتاه را بنویس" style="width:55%" />
    <select id="fileGenerateFormat"><option value="docx">Word (.docx)</option><option value="xlsx">Excel (.xlsx)</option><option value="pdf">PDF</option><option value="pptx">PowerPoint (.pptx)</option></select>
    <button type="button" id="fileGenerateButton">ساخت فایل</button>
  </div>
  <div id="fileStatus" class="small"></div>
</div>
<script src="/static/ui_extensions.js" defer></script>
"""


def install_ui_extensions(app) -> None:
    @app.middleware("http")
    async def local_feature_ui(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or not hasattr(response, "body") or not response.body:
            return response
        body = response.body.decode("utf-8", errors="replace")
        if 'id="localFileTools"' in body:
            return response
        body = body.replace("</body>", INJECT + "</body>")
        headers = {k: v for k, v in response.headers.items() if k.lower() not in {"content-length", "content-type"}}
        return HTMLResponse(body, status_code=response.status_code, headers=headers)
