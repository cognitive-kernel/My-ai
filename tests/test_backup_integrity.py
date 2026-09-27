import json
import pytest
from my_ai import db


def test_export_backup_contains_integrity_metadata(tmp_path, monkeypatch):
    from my_ai import platform
    monkeypatch.setattr(platform.settings, "db_path", str(tmp_path / "db.sqlite"))
    db.init_db()
    path = platform.export_database("integrity.json")
    payload = json.loads((platform.BACKUP_ROOT / "integrity.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["format_version"] >= 2
    assert len(payload["metadata"]["sha256"]) == 64
    assert platform.import_database(path)


def test_import_backup_rejects_tampering(tmp_path, monkeypatch):
    from my_ai import platform
    monkeypatch.setattr(platform.settings, "db_path", str(tmp_path / "db.sqlite"))
    db.init_db()
    path = platform.export_database("tamper.json")
    raw = json.loads((platform.BACKUP_ROOT / "tamper.json").read_text(encoding="utf-8"))
    raw["tables"]["knowledge"].append({"topic": "tampered", "title": "tampered", "content": "x"})
    (platform.BACKUP_ROOT / "tamper.json").write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        platform.import_database(path)
