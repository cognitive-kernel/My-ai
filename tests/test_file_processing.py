from pathlib import Path

from my_ai.file_processing import detect_type, generic_inspection, missing_prerequisites, missing_system_prerequisites


def test_detect_common_file_types(tmp_path: Path):
    image = tmp_path / "photo.png"
    image.write_bytes(b"x")
    assert detect_type(str(image))["kind"] == "image"

    workbook = tmp_path / "book.xlsx"
    workbook.write_bytes(b"x")
    assert detect_type(str(workbook))["kind"] == "spreadsheet"

    video = tmp_path / "clip.mkv"
    video.write_bytes(b"x")
    assert detect_type(str(video))["kind"] == "video"

    archive = tmp_path / "bundle.zip"
    archive.write_bytes(b"not-a-real-zip")
    assert detect_type(str(archive))["kind"] == "archive"


def test_missing_prerequisites_returns_known_package_names(monkeypatch):
    monkeypatch.setattr("my_ai.file_processing.importlib.util.find_spec", lambda name: None)
    assert missing_prerequisites("document") == ["python-docx"]
    assert missing_prerequisites("image") == ["Pillow"]


def test_media_requires_ffmpeg(monkeypatch):
    monkeypatch.setattr("my_ai.file_processing.shutil.which", lambda name: None)
    assert missing_system_prerequisites("audio") == ["ffmpeg", "ffprobe"]
    assert missing_system_prerequisites("video") == ["ffmpeg", "ffprobe"]
    assert missing_system_prerequisites("pdf") == []


def test_generic_inspection_is_read_only(tmp_path: Path):
    target = tmp_path / "unknown.bin"
    target.write_bytes(b"hello")
    result = generic_inspection(str(target))
    assert result["size"] == 5
    assert result["sha256"]
    assert target.read_bytes() == b"hello"


def test_system_prerequisite_catalog_is_allowlisted(monkeypatch):
    from my_ai import file_processing
    monkeypatch.setattr(file_processing.shutil, "which", lambda name: "/usr/bin/" + name if name in {"git", "ffmpeg"} else None)
    status = file_processing.system_prerequisite_status(["git", "ffmpeg", "nmap"])
    assert status == {"git": True, "ffmpeg": True, "nmap": False}
