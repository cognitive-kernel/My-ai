from __future__ import annotations

from fastapi.responses import HTMLResponse


INJECT = ""


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
