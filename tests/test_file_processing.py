from pathlib import Path

from my_ai.file_processing import detect_type, missing_prerequisites


def test_detect_common_file_types(tmp_path: Path):
    image = tmp_path / "photo.png"
    image.write_bytes(b"x")
    assert detect_type(str(image))["kind"] == "image"

    workbook = tmp_path / "book.xlsx"
    workbook.write_bytes(b"x")
    assert detect_type(str(workbook))["kind"] == "spreadsheet"


def test_missing_prerequisites_returns_known_package_names(monkeypatch):
    monkeypatch.setattr("my_ai.file_processing.importlib.util.find_spec", lambda name: None)
    assert missing_prerequisites("document") == ["python-docx"]
    assert missing_prerequisites("image") == ["Pillow"]
