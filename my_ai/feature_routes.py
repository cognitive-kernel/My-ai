from __future__ import annotations

import os
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .file_processing import create_docx, create_pdf, create_pptx, create_xlsx, detect_type, install_known_prerequisites, missing_prerequisites, missing_system_prerequisites
from .local_files import filesystem_roots, inspect_file, list_directory, read_text, workspace_path
from .multimodal import analyze
from .image_generation import generate_image, IMAGE_ROOT, ImageGenerationError


class FilePathRequest(BaseModel):
    path: str


class PrerequisiteRequest(BaseModel):
    path: str
    install_system: bool = False
    confirmed: bool = False


class GenerateDocxRequest(BaseModel):
    filename: str
    title: str
    paragraphs: list[str]


class GenerateXlsxRequest(BaseModel):
    filename: str
    sheets: dict[str, list[list[object]]]


class GeneratePdfRequest(BaseModel):
    filename: str
    title: str
    paragraphs: list[str]


class GeneratePptxRequest(BaseModel):
    filename: str
    title: str
    slides: list[dict[str, str]]


class GenerateFromChatRequest(BaseModel):
    prompt: str
    format: str
    filename: str


class ImageGenerateRequest(BaseModel):
    prompt: str
    size: str = "1024x1024"
    quality: str = "high"
    negative_prompt: str = ""


def _normalise_format(value: str) -> str:
    value = value.strip().lower().lstrip(".")
    aliases = {"word": "docx", "doc": "docx", "excel": "xlsx", "xls": "xlsx", "powerpoint": "pptx", "power-point": "pptx", "presentation": "pptx", "pdf": "pdf"}
    return aliases.get(value, value)


def _chat_content(prompt: str, fmt: str) -> tuple[str, list[str], list[dict[str, str]]]:
    clean = prompt.strip()
    title = clean[:120] or "My-AI document"
    paragraphs = [clean]
    slides = [{"title": title, "body": clean}]
    return title, paragraphs, slides


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
        # Custom Courses (for example Cisco) have their own runner and must
        # not be resumed through the standard language Scheduler.
        from .settings_feature import start_named_course
        course_id = start_named_course(language)
        if course_id is not None:
            audit(user, "learning", "write", "200", f"resumed-custom:{language}:{course_id}")
            return {"status": "running", "language": language, "course_id": course_id, "custom_course": True}
        scheduler.start(language)
        audit(user, "learning", "write", "200", f"resumed:{language}")
        return {"status": "running", "language": language}

    @router.post("/image/generate")
    def image_generate(payload: ImageGenerateRequest, request: Request):
        user = require_user(request)
        try:
            result = generate_image(payload.prompt, payload.size, payload.quality, payload.negative_prompt)
        except ImageGenerationError as exc:
            raise HTTPException(502, str(exc))
        audit(user, "image-generation", "execute", "200", f"generated:{result['filename']}")
        return {**result, "url": f"/image/file/{result['filename']}"}

    @router.get("/image/file/{filename}")
    def image_file(filename: str, request: Request):
        from fastapi.responses import FileResponse
        require_user(request)
        path = (IMAGE_ROOT / Path(filename).name).resolve()
        try:
            path.relative_to(IMAGE_ROOT)
        except ValueError:
            raise HTTPException(400, "Invalid image path.")
        if not path.is_file():
            raise HTTPException(404, "Generated image not found.")
        return FileResponse(path)

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

    @router.get("/files/download")
    def files_download(path: str, request: Request):
        require_user(request)
        candidate = Path(path).expanduser().resolve()
        try:
            candidate.relative_to(workspace_path("").resolve())
        except ValueError:
            raise HTTPException(400, "Only files in the My-AI workspace can be downloaded.")
        if not candidate.is_file():
            raise HTTPException(404, "File not found.")
        return FileResponse(candidate, filename=candidate.name, media_type="application/octet-stream")

    @router.post("/files/analyze")
    def files_analyze(payload: FilePathRequest, request: Request):
        require_user(request)
        info = detect_type(payload.path)
        missing = missing_prerequisites(info["kind"])
        install_system = os.getenv("MYAI_AUTO_INSTALL_SYSTEM_PREREQUISITES", "false").strip().lower() == "true"
        prerequisites = install_known_prerequisites(info["kind"], install_system=install_system) if missing or missing_system_prerequisites(info["kind"]) else {"python_installed": [], "system_missing": [], "system_installed": []}
        result = analyze(payload.path)
        result["prerequisites"] = {"missing_before": missing, **prerequisites}
        return result

    @router.post("/files/prerequisites")
    def files_prerequisites(payload: PrerequisiteRequest, request: Request):
        user = require_admin(request) if payload.install_system else require_user(request)
        kind = detect_type(payload.path)["kind"]
        if payload.install_system and not payload.confirmed:
            raise HTTPException(409, "System prerequisite installation requires explicit confirmation.")
        result = install_known_prerequisites(kind, install_system=payload.install_system)
        return {"kind": kind, "missing_before": missing_prerequisites(kind), **result, "actor": user.get("username")}

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

    @router.post("/files/generate/pdf")
    def files_generate_pdf(payload: GeneratePdfRequest, request: Request):
        user = require_user(request)
        path = create_pdf(str(workspace_path(payload.filename)), payload.title, payload.paragraphs)
        audit(user, "files", "write", "201", f"generated:{path}")
        return {"path": path, "local_path": path, "read_only_after_creation": True}

    @router.post("/files/generate/pptx")
    def files_generate_pptx(payload: GeneratePptxRequest, request: Request):
        user = require_user(request)
        path = create_pptx(str(workspace_path(payload.filename)), payload.title, payload.slides)
        audit(user, "files", "write", "201", f"generated:{path}")
        return {"path": path, "local_path": path, "read_only_after_creation": True}

    @router.post("/files/generate/from-chat")
    def files_generate_from_chat(payload: GenerateFromChatRequest, request: Request):
        user = require_user(request)
        fmt = _normalise_format(payload.format)
        title, paragraphs, slides = _chat_content(payload.prompt, fmt)
        filename = payload.filename.strip() or f"myai-generated.{fmt}"
        if fmt == "docx":
            path = create_docx(str(workspace_path(filename)), title, paragraphs)
        elif fmt == "xlsx":
            path = create_xlsx(str(workspace_path(filename)), {"Sheet1": [[title], [payload.prompt]]})
        elif fmt == "pdf":
            path = create_pdf(str(workspace_path(filename)), title, paragraphs)
        elif fmt == "pptx":
            path = create_pptx(str(workspace_path(filename)), title, slides)
        else:
            raise HTTPException(400, "format must be docx, xlsx, pdf, or pptx")
        audit(user, "files", "write", "201", f"generated-from-chat:{path}")
        return {"path": path, "local_path": path, "format": fmt, "source_prompt": payload.prompt, "read_only_after_creation": True}

    app.include_router(router)
