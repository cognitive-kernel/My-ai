import json
import pytest
from my_ai import db


def test_export_backup_contains_integrity_metadata(tmp_path, monkeypatch):
    from my_ai import platform
    monkeypatch.setattr(platform, "BACKUP_ROOT", tmp_path / "backups")
    db.init_db()
    path = platform.export_database(str(tmp_path / "backups" / "integrity.json"))
    payload = json.loads((tmp_path / "backups" / "integrity.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["format_version"] >= 2
    assert len(payload["metadata"]["sha256"]) == 64
    assert platform.import_database(path) == {}


def test_import_backup_rejects_tampering(tmp_path, monkeypatch):
    from my_ai import platform
    monkeypatch.setattr(platform, "BACKUP_ROOT", tmp_path / "backups")
    db.init_db()
    path = platform.export_database(str(tmp_path / "backups" / "tamper.json"))
    raw = json.loads((tmp_path / "backups" / "tamper.json").read_text(encoding="utf-8"))
    raw["tables"]["knowledge"].append({"topic": "tampered", "title": "tampered", "content": "x"})
    (tmp_path / "backups" / "tamper.json").write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        platform.import_database(path)


def test_encrypted_export_is_verifiable(tmp_path, monkeypatch):
    from my_ai import platform
    monkeypatch.setattr(platform, "BACKUP_ROOT", tmp_path / "backups")
    db.init_db()
    path = platform.export_database(str(tmp_path / "backups" / "encrypted.json"), password="strong-backup-password")
    result = platform.verify_backup(path, password="strong-backup-password")
    assert result["valid"] is True
    assert result["type"] == "encrypted-json"
    with pytest.raises(Exception):
        platform.verify_backup(path, password="wrong-password")
