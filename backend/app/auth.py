from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any

ROLE_VIEWER = "viewer"
ROLE_PLANNER = "planner"
ROLE_ADMIN = "admin"
ALLOWED_ROLES = {ROLE_VIEWER, ROLE_PLANNER, ROLE_ADMIN}

SESSION_COOKIE_NAME = "retreat_ops_session"
DEFAULT_SESSION_HOURS = 24 * 14

BOOTSTRAP_ADMIN_USERNAME_ENV = "RETREAT_OPS_BOOTSTRAP_ADMIN_USERNAME"
BOOTSTRAP_ADMIN_PASSWORD_ENV = "RETREAT_OPS_BOOTSTRAP_ADMIN_PASSWORD"
SESSION_HOURS_ENV = "RETREAT_OPS_SESSION_HOURS"
COOKIE_SECURE_ENV = "RETREAT_OPS_COOKIE_SECURE"
COOKIE_SECURE_DISABLED = {"0", "false", "off", "no"}


@dataclass(frozen=True)
class AuthUser:
    id: int
    username: str
    role: str
    is_active: bool


def normalize_role(role: str) -> str:
    value = str(role or "").strip().lower()
    if value not in ALLOWED_ROLES:
        raise ValueError(f"Unknown role '{role}'. Allowed roles: {', '.join(sorted(ALLOWED_ROLES))}")
    return value


def session_hours() -> int:
    raw = os.getenv(SESSION_HOURS_ENV, str(DEFAULT_SESSION_HOURS)).strip()
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_SESSION_HOURS
    return max(1, parsed)


def cookie_secure_enabled() -> bool:
    raw = os.getenv(COOKIE_SECURE_ENV, "0").strip().lower()
    return raw not in COOKIE_SECURE_DISABLED


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    salt = secrets.token_bytes(16)
    n, r, p = 2**14, 8, 1
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32)
    return "scrypt${}${}${}${}${}".format(
        n,
        r,
        p,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(derived).decode("ascii"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, n_raw, r_raw, p_raw, salt_raw, expected_raw = stored_hash.split("$", 5)
        if algo != "scrypt":
            return False
        n, r, p = int(n_raw), int(r_raw), int(p_raw)
        salt = base64.urlsafe_b64decode(salt_raw.encode("ascii"))
        expected = base64.urlsafe_b64decode(expected_raw.encode("ascii"))
    except Exception:
        return False

    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=len(expected))
    return hmac.compare_digest(derived, expected)


def hash_session_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def cleanup_expired_sessions(conn: Any) -> None:
    conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (int(time.time()),))


def ensure_bootstrap_admin(conn: Any) -> bool:
    username = os.getenv(BOOTSTRAP_ADMIN_USERNAME_ENV, "").strip()
    password = os.getenv(BOOTSTRAP_ADMIN_PASSWORD_ENV, "").strip()
    if not username or not password:
        return False

    existing = conn.execute(
        "SELECT id FROM users WHERE lower(username) = lower(?)",
        (username,),
    ).fetchone()
    if existing:
        return False

    conn.execute(
        """
        INSERT INTO users(username, password_hash, role, is_active)
        VALUES (?, ?, ?, 1)
        """,
        (username, hash_password(password), ROLE_ADMIN),
    )
    return True


def has_any_users(conn: Any) -> bool:
    row = conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
    return bool(row)


def create_user(conn: Any, username: str, password: str, role: str, *, is_active: bool = True) -> AuthUser:
    clean_username = " ".join(str(username or "").strip().split())
    if not clean_username:
        raise ValueError("Username cannot be blank")
    if not password:
        raise ValueError("Password cannot be blank")
    clean_role = normalize_role(role)

    row = conn.execute(
        """
        INSERT INTO users(username, password_hash, role, is_active)
        VALUES (?, ?, ?, ?)
        RETURNING id, username, role, is_active
        """,
        (clean_username, hash_password(password), clean_role, 1 if is_active else 0),
    ).fetchone()
    return AuthUser(
        id=int(row["id"]),
        username=row["username"],
        role=row["role"],
        is_active=bool(row["is_active"]),
    )


def update_user(
    conn: Any,
    user_id: int,
    *,
    password: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
) -> AuthUser:
    current = conn.execute(
        "SELECT id, username, role, is_active FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if not current:
        raise ValueError("User not found")

    updates: list[str] = []
    values: list[Any] = []

    if password is not None:
        if not password:
            raise ValueError("Password cannot be blank")
        updates.append("password_hash = ?")
        values.append(hash_password(password))

    if role is not None:
        updates.append("role = ?")
        values.append(normalize_role(role))

    if is_active is not None:
        updates.append("is_active = ?")
        values.append(1 if is_active else 0)

    if updates:
        values.append(user_id)
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", values)

    updated = conn.execute(
        "SELECT id, username, role, is_active FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return AuthUser(
        id=int(updated["id"]),
        username=updated["username"],
        role=updated["role"],
        is_active=bool(updated["is_active"]),
    )


def authenticate_credentials(conn: Any, username: str, password: str) -> AuthUser | None:
    clean_username = str(username or "").strip()
    if not clean_username or not password:
        return None

    row = conn.execute(
        """
        SELECT id, username, role, is_active, password_hash
        FROM users
        WHERE lower(username) = lower(?)
        """,
        (clean_username,),
    ).fetchone()
    if not row:
        return None
    if not bool(row["is_active"]):
        return None
    if not verify_password(password, row["password_hash"]):
        return None

    return AuthUser(
        id=int(row["id"]),
        username=row["username"],
        role=row["role"],
        is_active=bool(row["is_active"]),
    )


def create_session(conn: Any, user_id: int) -> str:
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_session_token(raw_token)
    now = int(time.time())
    expires_at = now + session_hours() * 3600

    conn.execute(
        """
        INSERT INTO auth_sessions(user_id, token_hash, expires_at)
        VALUES (?, ?, ?)
        """,
        (user_id, token_hash, expires_at),
    )
    return raw_token


def authenticate_session_token(conn: Any, raw_token: str) -> AuthUser | None:
    if not raw_token:
        return None

    cleanup_expired_sessions(conn)

    row = conn.execute(
        """
        SELECT
            s.id AS session_id,
            u.id AS user_id,
            u.username,
            u.role,
            u.is_active
        FROM auth_sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ?
          AND s.expires_at > ?
        LIMIT 1
        """,
        (hash_session_token(raw_token), int(time.time())),
    ).fetchone()
    if not row:
        return None
    if not bool(row["is_active"]):
        return None

    conn.execute(
        "UPDATE auth_sessions SET last_seen_at = CURRENT_TIMESTAMP WHERE id = ?",
        (row["session_id"],),
    )

    return AuthUser(
        id=int(row["user_id"]),
        username=row["username"],
        role=row["role"],
        is_active=bool(row["is_active"]),
    )


def delete_session(conn: Any, raw_token: str | None) -> None:
    if not raw_token:
        return
    conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (hash_session_token(raw_token),))


def list_users(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, username, role, is_active, created_at
        FROM users
        ORDER BY lower(username), id
        """
    ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "username": row["username"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def default_route_for_role(role: str) -> str:
    normalized = normalize_role(role)
    if normalized in {ROLE_ADMIN, ROLE_PLANNER}:
        return "/retreat-planner-sample.html"
    return "/kitchen-service-view.html"
