import os

import pytest

from my_ai import auth, db


@pytest.fixture()
def isolated_db(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "auth.db"))
    db.init_db()
    yield
    object.__setattr__(db.settings, "db_path", old)


def test_first_account_is_admin_and_second_is_user(isolated_db):
    first = auth.create_account("owner", "a-secure-password", "Owner")
    second = auth.create_account("member", "another-secure-password", "Member")
    assert first["role"] == "admin"
    assert second["role"] == "user"


def test_password_authentication_and_tool_permission(isolated_db):
    admin = auth.create_account("owner", "a-secure-password")
    user = auth.create_account("member", "another-secure-password")
    assert auth.authenticate("owner", "wrong-password") is None
    authenticated = auth.authenticate("owner", "a-secure-password")
    assert authenticated["id"] == admin["id"]
    assert auth.tool_allowed(authenticated, "scheduler", "execute") is True
    authenticated_user = auth.authenticate("member", "another-secure-password")
    assert auth.tool_allowed(authenticated_user, "scheduler", "execute") is False
    db.execute(
        "INSERT INTO tool_permissions(user_id,tool_name,action,allowed) VALUES(?,?,?,1)",
        (user["id"], "scheduler", "execute"),
    )
    assert auth.tool_allowed(authenticated_user, "scheduler", "execute") is True


def test_admin_always_has_tool_access(isolated_db):
    admin = auth.create_account("owner", "a-secure-password")
    assert auth.tool_allowed(admin, "anything", "write") is True


def test_concurrent_first_accounts_create_only_one_admin(isolated_db):
    from concurrent.futures import ThreadPoolExecutor
    def create(i):
        return auth.create_account(f"member{i}", "a-secure-password")
    with ThreadPoolExecutor(max_workers=2) as pool:
        users=list(pool.map(create, (1,2)))
    assert sorted(u["role"] for u in users) == ["admin", "user"]
