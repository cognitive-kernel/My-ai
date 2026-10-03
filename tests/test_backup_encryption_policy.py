from pathlib import Path

import pytest

from my_ai import backup_manager


def test_encrypted_backup_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "source.db"
    db.write_bytes(b"SQLite-like backup payload")
    monkeypatch.setattr(backup_manager, "DB_PATH", str(db))
    monkeypatch.setattr(
        backup_manager,
        "get_setting",
        lambda key, default=None: "aes-gcm" if key == "database.backup.encryption" else "correct-horse-battery-staple",
    )

    destination = tmp_path / "backup.db"
    result = backup_manager.backup(str(destination))
    assert result["encrypted"] is True
    assert destination.read_bytes() != db.read_bytes()

    restored = tmp_path / "restored.db"
    monkeypatch.setattr(backup_manager, "DB_PATH", str(restored))
    assert backup_manager.restore(str(destination))["encrypted"] is True
    assert restored.read_bytes() == db.read_bytes()


def test_encrypted_backup_rejects_wrong_password(tmp_path):
    db = tmp_path / "source.db"
    db.write_bytes(b"payload")
    original = backup_manager.DB_PATH
    try:
        backup_manager.DB_PATH = str(db)
        destination = tmp_path / "backup.db"
        backup_manager.backup(str(destination), password="correct-horse-battery-staple")
        backup_manager.DB_PATH = str(tmp_path / "restored.db")
        with pytest.raises(Exception):
            backup_manager.restore(
                str(destination),
                password="wrong-password",
            )
    finally:
        backup_manager.DB_PATH = original


def test_encryption_policy_rejects_short_configured_password(monkeypatch):
    monkeypatch.setattr(backup_manager, "get_setting", lambda key, default=None: "aes-gcm" if key == "database.backup.encryption" else "short")
    with pytest.raises(ValueError, match="at least 12"):
        backup_manager._encryption_password()
