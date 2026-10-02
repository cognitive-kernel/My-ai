import pytest

from my_ai import db


@pytest.fixture
def client_db(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "client.db"))
    db.init_db()
    try:
        yield db.settings.db_path
    finally:
        object.__setattr__(db.settings, "db_path", old)
