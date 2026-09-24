from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from .file_processing import create_docx, create_xlsx, install_known_prerequisites
from .local_files import filesystem_roots, inspect_file, list_directory, read_text, workspace_path
from .multimodal import analyze


class FilePathRequest(BaseModel):
    path: str


class GenerateDocxRequest(BaseModel):
    filename: str
    title: str
    paragraphs: list[str]


class GenerateXlsxRequest(BaseModel):
    filename: str
    sheets: dict[str, list[list[object]]]


def register_routes(app, scheduler, require_user, audit):
    router = APIRouter()

    @router.get("/learning/controls")
    def learning_controls(request: Request):
        require_user(request)
        return scheduler.status()

    @router.post("/learning/{language}/stop")
    def learning_stop(language: str, request: Request):
        user = require_user(request)
        scheduler.stop_learning(language)
        audit(user, "learning", "write", "200", f"stopped:{language}")
        return {"status": "stopping", "language": language}

    @router.post("/learning/{language}/resume")
    def learning_resume(language: str, request: Request):
        user = require_user(request)
        scheduler.start(language)
        audit(user, "learning", "write", "200", f"resumed:{language}")
        return {"status": "running", "language": language}

    @router.get("/files/roots")
    def files_roots(request: Request):
        require_user(request)
        return {"roots": filesystem_roots(), "read_only": True}

    @router.get("/files/list")
    def files_list(path: str, request: Request):
        require_user(request)
        return {"path": str(Path(path).expanduser().resolve()), "items": list_directory(path), "read_only": True}

    @router.post("/files/inspect")
    def files_inspect(payload: FilePathRequest, request: Request):
        require_user(request)
        return inspect_file(payload.path)

    @router.post("/files/read")
    def files_read(payload: FilePathRequest, request: Request):
        require_user(request)
        return {"path": payload.path, "text": read_text(payload.path), "read_only": True}

    @router.post("/files/upload")
    async def files_upload(request: Request, file: UploadFile = File(...)):
        user = require_user(request)
        if not file.filename:
            raise HTTPException(400, "A filename is required.")
        target = workspace_path(file.filename)
        data = await file.read()
        if len(data) > 100 * 1024 * 1024:
            raise HTTPException(413, "Uploaded files are limited to 100 MiB.")
        target.write_bytes(data)
        audit(user, "files", "write", "201", f"uploaded:{target.name}")
        return {"path": str(target), "name": target.name, "size": len(data), "stored_in": str(target.parent)}

    @router.post("/files/analyze")
    def files_analyze(payload: FilePathRequest, request: Request):
        require_user(request)
        return analyze(payload.path)

    @router.post("/files/prerequisites")
    def files_prerequisites(payload: FilePathRequest, request: Request):
        require_user(request)
        from .file_processing import detect_type, missing_prerequisites
        kind = detect_type(payload.path)["kind"]
        missing = missing_prerequisites(kind)
        installed = install_known_prerequisites(kind) if missing else []
        return {"kind": kind, "missing_before": missing, "installed": installed}

    @router.post("/files/generate/docx")
    def files_generate_docx(payload: GenerateDocxRequest, request: Request):
        user = require_user(request)
        path = create_docx(str(workspace_path(payload.filename)), payload.title, payload.paragraphs)
        audit(user, "files", "write", "201", f"generated:{path}")
        return {"path": path, "local_path": path, "read_only_after_creation": True}

    @router.post("/files/generate/xlsx")
    def files_generate_xlsx(payload: GenerateXlsxRequest, request: Request):
        user = require_user(request)
        path = create_xlsx(str(workspace_path(payload.filename)), payload.sheets)
        audit(user, "files", "write", "201", f"generated:{path}")
        return {"path": path, "local_path": path, "read_only_after_creation": True}

    app.include_router(router)
