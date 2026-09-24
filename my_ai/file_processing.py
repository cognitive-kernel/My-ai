from __future__ import annotations

import importlib.util
import mimetypes
import subprocess
import sys
from pathlib import Path
from typing import Any

OPTIONAL_PREREQUISITES: dict[str, str] = {
    "docx": "python-docx",
    "openpyxl": "openpyxl",
    "pptx": "python-pptx",
    "fitz": "PyMuPDF",
    "PIL": "Pillow",
}


def detect_type(path: str) -> dict[str, str]:
    p = Path(path)
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    kind = "unknown"
    if mime.startswith("image/"):
        kind = "image"
    elif mime.startswith("audio/"):
        kind = "audio"
    elif mime.startswith("video/"):
        kind = "video"
    elif mime.startswith("text/") or p.suffix.lower() in {".py", ".js", ".ts", ".json", ".yaml", ".yml", ".xml", ".md", ".csv", ".log"}:
        kind = "text"
    elif p.suffix.lower() in {".doc", ".docx"}:
        kind = "document"
    elif p.suffix.lower() in {".xls", ".xlsx"}:
        kind = "spreadsheet"
    elif p.suffix.lower() in {".ppt", ".pptx"}:
        kind = "presentation"
    elif p.suffix.lower() == ".pdf":
        kind = "pdf"
    return {"mime_type": mime, "kind": kind, "extension": p.suffix.lower()}


def missing_prerequisites(kind: str) -> list[str]:
    imports = {
        "document": ["docx"],
        "spreadsheet": ["openpyxl"],
        "presentation": ["pptx"],
        "pdf": ["fitz"],
        "image": ["PIL"],
    }
    return [OPTIONAL_PREREQUISITES[name] for name in imports.get(kind, []) if importlib.util.find_spec(name) is None]


def install_known_prerequisites(kind: str) -> list[str]:
    packages = missing_prerequisites(kind)
    installed: list[str] = []
    for package in packages:
        subprocess.run([sys.executable, "-m", "pip", "install", package], check=True, timeout=600)
        installed.append(package)
    return installed


def extract_text(path: str) -> dict[str, Any]:
    p = Path(path)
    info = detect_type(path)
    if info["kind"] == "text":
        return {"kind": "text", "text": p.read_text(encoding="utf-8", errors="replace")}
    if info["kind"] == "document":
        from docx import Document
        doc = Document(str(p))
        return {"kind": "document", "text": "\n".join(x.text for x in doc.paragraphs)}
    if info["kind"] == "spreadsheet":
        from openpyxl import load_workbook
        wb = load_workbook(str(p), read_only=True, data_only=True)
        sheets = {ws.title: [[cell.value for cell in row] for row in ws.iter_rows()] for ws in wb.worksheets}
        return {"kind": "spreadsheet", "sheets": sheets}
    if info["kind"] == "pdf":
        import fitz
        doc = fitz.open(str(p))
        return {"kind": "pdf", "text": "\n".join(page.get_text() for page in doc), "pages": len(doc)}
    raise ValueError(f"No text extractor is registered for {p.suffix or 'this file type'}")


def create_docx(path: str, title: str, paragraphs: list[str]) -> str:
    from docx import Document
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.add_heading(title, level=1)
    for paragraph in paragraphs:
        doc.add_paragraph(paragraph)
    doc.save(str(output))
    return str(output.resolve())


def create_xlsx(path: str, sheets: dict[str, list[list[Any]]]) -> str:
    from openpyxl import Workbook
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    first = True
    for name, rows in sheets.items():
        ws = wb.active if first else wb.create_sheet()
        first = False
        ws.title = name[:31] or "Sheet1"
        for row in rows:
            ws.append(row)
    wb.save(str(output))
    return str(output.resolve())


def create_pdf(path: str, title: str, paragraphs: list[str]) -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(output), pagesize=A4)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    story.extend(Paragraph(p, styles["BodyText"]) for p in paragraphs)
    doc.build(story)
    return str(output.resolve())


def create_pptx(path: str, title: str, slides: list[dict[str, str]]) -> str:
    from pptx import Presentation
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    presentation = Presentation()
    first = presentation.slides.add_slide(presentation.slide_layouts[0])
    first.shapes.title.text = title
    for slide_data in slides:
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = str(slide_data.get("title", ""))
        slide.placeholders[1].text = str(slide_data.get("body", ""))
    presentation.save(str(output))
    return str(output.resolve())
