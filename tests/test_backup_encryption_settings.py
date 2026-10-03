import pytest


def test_backup_manager_encrypts_and_restores(tmp_path, monkeypatch):
    from my_ai import backup_manager
    source = tmp_path / "db.sqlite"
    source.write_bytes(b"secret-db-bytes")
    monkeypatch.setattr(backup_manager, "DB_PATH", str(source))
    encrypted = tmp_path / "backup.sqlite.enc"
    result = backup_manager.backup(str(encrypted), password="correct-horse-battery")
    assert result["encrypted"] is True
    assert encrypted.read_bytes() != source.read_bytes()
    restored = tmp_path / "restored.sqlite"
    result = backup_manager.restore(str(encrypted), target=str(restored), password="correct-horse-battery")
    assert result["size"] == len(b"secret-db-bytes")
    assert restored.read_bytes() == source.read_bytes()
    with pytest.raises(Exception):
        backup_manager.restore(str(encrypted), target=str(tmp_path / "bad.sqlite"), password="wrong-password")


def test_backup_manager_plain_mode_remains_supported(tmp_path, monkeypatch):
    from my_ai import backup_manager
    source = tmp_path / "db.sqlite"
    source.write_bytes(b"plain-db")
    monkeypatch.setattr(backup_manager, "DB_PATH", str(source))
    destination = tmp_path / "backup.sqlite"
    result = backup_manager.backup(str(destination))
    assert result["encrypted"] is False
    assert destination.read_bytes() == source.read_bytes()
