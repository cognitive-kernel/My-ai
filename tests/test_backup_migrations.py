import hashlib
import json

from my_ai import db, platform


def test_import_accepts_legacy_format_v2_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(platform, "BACKUP_ROOT", tmp_path / "backups")
    db.init_db()
    tables = {
        "knowledge": [{"topic": "legacy", "title": "legacy", "content": "compatible", "content_hash": "legacy-1"}],
    }
    canonical = json.dumps(tables, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    payload = {
        "metadata": {
            "format_version": 2,
            "app_version": "legacy",
            "sha256": hashlib.sha256(canonical).hexdigest(),
            "encrypted": False,
        },
        "tables": tables,
    }
    path = tmp_path / "backups" / "legacy-v2.json"
    path.parent.mkdir()
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result = platform.import_database(str(path))
    assert result["knowledge"] == 1
    assert db.fetch_all("SELECT content FROM knowledge WHERE title='legacy'")[0]["content"] == "compatible"
