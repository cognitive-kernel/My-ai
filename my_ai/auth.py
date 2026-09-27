from __future__ import annotations

import hashlib
import json
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, Request

from .db import connect, execute, fetch_all


SESSION_TTL_HOURS = 24


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if not password or len(password) < 10:
        raise ValueError("Password must be at least 10 characters.")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, digest_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def has_users() -> bool:
    return bool(fetch_all("SELECT id FROM users LIMIT 1"))


def create_account(username: str, password: str, display_name: str = "") -> dict[str, Any]:
    username = username.strip().lower()
    if len(username) < 3:
        raise ValueError("Username must contain at least 3 characters.")
    if not password:
        raise ValueError("Password is required.")
    salt, digest = _hash_password(password)
    display_name = display_name.strip()[:120]
    try:
        with connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM users WHERE username=?",(username,)).fetchone():
                raise ValueError("Username already exists.")
            role = "admin" if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone() is None else "user"
            cur=conn.execute(
                "INSERT INTO users(username,password_salt,password_hash,display_name,role) VALUES(?,?,?,?,?)",
                (username,salt,digest,display_name,role),
            )
            if cur.lastrowid is None:
                raise RuntimeError("User insert did not return an id.")
            user_id=int(cur.lastrowid)
            conn.commit()
    except ValueError:
        raise
    except sqlite3.IntegrityError as exc:
        raise ValueError("Username already exists.") from exc
    return {"id":user_id,"username":username,"display_name":display_name,"role":role}


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    rows = fetch_all(
        "SELECT id,username,password_salt,password_hash,display_name,role,active FROM users WHERE username=?",
        (username.strip().lower(),),
    )
    if not rows or not rows[0]["active"]:
        return None
    user = rows[0]
    if not verify_password(password, user["password_salt"], user["password_hash"]):
        return None
    return {k: user[k] for k in ("id", "username", "display_name", "role")}


def create_session(user_id: int) -> str:
    execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (datetime.now(timezone.utc).isoformat(),))
    token = secrets.token_urlsafe(48)
    expires = (datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).isoformat()
    execute("INSERT INTO auth_sessions(token,user_id,expires_at) VALUES(?,?,?)", (token, user_id, expires))
    return token


def revoke_session(token: str) -> None:
    execute("DELETE FROM auth_sessions WHERE token=?", (token,))


def current_user(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get("myai_session")
    if not token:
        return None
    rows = fetch_all(
        """SELECT u.id,u.username,u.display_name,u.role,u.active
           FROM auth_sessions s JOIN users u ON u.id=s.user_id
           WHERE s.token=? AND s.expires_at > ?""",
        (token, datetime.now(timezone.utc).isoformat()),
    )
    if not rows or not rows[0]["active"]:
        return None
    return rows[0]


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(401, "Authentication required.")
    return user


def require_admin(request: Request) -> dict[str, Any]:
    user = require_user(request)
    if user["role"] != "admin":
        raise HTTPException(403, "Administrator access required.")
    return user


def tool_allowed(user: dict[str, Any], tool_name: str, action: str = "execute") -> bool:
    if user["role"] == "admin":
        return True
    rows = fetch_all(
        "SELECT allowed FROM tool_permissions WHERE user_id=? AND tool_name=? AND action=?",
        (user["id"], tool_name, action),
    )
    return bool(rows and rows[0]["allowed"])


def require_tool(user: dict[str, Any], tool_name: str, action: str = "execute") -> None:
    if not tool_allowed(user, tool_name, action):
        raise HTTPException(403, f"Tool permission denied: {tool_name}:{action}")


def audit(
    user: dict[str, Any] | None,
    tool_name: str,
    action: str,
    status: str,
    details: str = "",
) -> None:
    execute(
        """INSERT INTO audit_log(user_id,username,tool_name,action,status,details)
           VALUES(?,?,?,?,?,?)""",
        (
            user["id"] if user else None,
            user["username"] if user else "anonymous",
            tool_name,
            action,
            status,
            details[:4000],
        ),
    )


def audit_event(
    user: dict[str, Any] | None,
    tool_name: str,
    action: str,
    status: str,
    *,
    request_id: str | None = None,
    input_data: bytes | str | None = None,
    output_data: bytes | str | None = None,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    def digest(value: bytes | str | None) -> str | None:
        if value is None:
            return None
        raw = value if isinstance(value, bytes) else value.encode("utf-8", "replace")
        return hashlib.sha256(raw).hexdigest()

    def size(value: bytes | str | None) -> int | None:
        if value is None:
            return None
        return len(value) if isinstance(value, bytes) else len(value.encode("utf-8", "replace"))

    payload: dict[str, Any] = {
        "request_id": request_id,
        "actor": {
            "id": user.get("id") if user else None,
            "username": user.get("username") if user else "anonymous",
            "role": user.get("role") if user else None,
        },
        "input": {"sha256": digest(input_data), "bytes": size(input_data)},
        "output": {"sha256": digest(output_data), "bytes": size(output_data)},
        "error": str(error)[:1000] if error else None,
    }
    if extra:
        payload["extra"] = extra
    audit(user, tool_name, action, status, json.dumps(payload, ensure_ascii=False, separators=(",", ":")))




# Route authorization is defined centrally so API middleware and tests share one policy.
from . import access_policy as _access_policy
TOOL_RULES = _access_policy.TOOL_RULES
PATH_ACTIONS = _access_policy.PATH_ACTIONS
permission_for_path = _access_policy.permission_for_path
