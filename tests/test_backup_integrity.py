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


def test_encrypted_export_contains_security_and_learning_state(tmp_path, monkeypatch):
    from my_ai import platform
    monkeypatch.setattr(platform, "BACKUP_ROOT", tmp_path / "backups")
    from my_ai import db
    db.init_db()
    path = platform.export_database(
        str(tmp_path / "backups" / "complete.json"),
        password="complete-backup-password",
    )
    from my_ai.backup_crypto import decrypt_bytes
    raw = decrypt_bytes((tmp_path / "backups" / "complete.json").read_bytes(), "complete-backup-password")
    import json
    payload = json.loads(raw.decode("utf-8"))
    assert payload["metadata"]["format_version"] >= 4
    assert payload["metadata"]["encrypted"] is True
    assert {"users", "tool_permissions", "audit_log", "skills", "skill_evidence"}.issubset(payload["tables"])


def test_restore_encrypted_backup_roundtrip(tmp_path, monkeypatch):
    from my_ai import platform
    monkeypatch.setattr(platform, "BACKUP_ROOT", tmp_path / "backups")
    db.init_db()
    db.execute("INSERT INTO knowledge(topic,title,content,content_hash) VALUES(?,?,?,?)", ("restore","probe","before","restore-probe"))
    source = platform.backup_database(str(tmp_path / "backups" / "roundtrip.sqlite.enc"), password="roundtrip-password")
    destination = str(tmp_path / "backups" / "restored.sqlite")
    restored = platform.restore_encrypted_backup(source, destination, "roundtrip-password")
    import sqlite3
    conn = sqlite3.connect(restored)
    assert conn.execute("SELECT content FROM knowledge WHERE title=?", ("probe",)).fetchone()[0] == "before"
    conn.close()


def test_encrypted_restore_rejects_wrong_password(tmp_path, monkeypatch):
    from my_ai import platform
    monkeypatch.setattr(platform, "BACKUP_ROOT", tmp_path / "backups")
    db.init_db()
    source = platform.backup_database(str(tmp_path / "backups" / "wrong-password.sqlite.enc"), password="correct-password")
    with pytest.raises(Exception):
        platform.restore_encrypted_backup(source, str(tmp_path / "backups" / "bad.sqlite"), "wrong-password")
