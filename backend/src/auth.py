"""Username/password accounts with token-based sessions.

Users live in a small SQLite file (no extra services needed). Passwords are
hashed with scrypt and never stored in plain text. A successful login returns a
signed JWT that the frontend sends with every request.
"""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("AUTH_DB_PATH", BASE_DIR / "data" / "users.db"))
TOKEN_HOURS = int(os.getenv("TOKEN_HOURS", "24"))
ALGORITHM = "HS256"
USERNAME_RE = re.compile(r"^[a-z0-9_.-]{3,30}$")


def _load_secret() -> str:
    """Use JWT_SECRET if set (recommended in production); otherwise keep a
    random secret in data/.jwt_secret so logins survive a dev-server restart."""
    from_env = os.getenv("JWT_SECRET")
    if from_env:
        return from_env
    secret_file = BASE_DIR / "data" / ".jwt_secret"
    try:
        if secret_file.exists():
            return secret_file.read_text().strip()
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        secret = secrets.token_hex(32)
        secret_file.write_text(secret)
        return secret
    except OSError:
        return secrets.token_hex(32)


SECRET_KEY = _load_secret()


# ---------- storage ----------

def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


_init_db()


# ---------- passwords ----------

def _scrypt(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return f"scrypt${salt.hex()}${_scrypt(password, salt).hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, hash_hex = stored.split("$")
        digest = _scrypt(password, bytes.fromhex(salt_hex)).hex()
    except ValueError:
        return False
    return hmac.compare_digest(digest, hash_hex)


_DUMMY_HASH = hash_password("placeholder-for-unknown-users")


# ---------- tokens ----------

def create_token(user_id: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    return jwt.encode({"sub": str(user_id), "exp": expires}, SECRET_KEY, algorithm=ALGORITHM)


def _public(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "username": row["username"], "full_name": row["full_name"]}


bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> dict:
    """Dependency that protects an endpoint: only signed-in users get through."""
    unauthorized = {"WWW-Authenticate": "Bearer"}
    if credentials is None:
        raise HTTPException(401, "Sign in to continue.", headers=unauthorized)
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Your session has expired. Sign in again.", headers=unauthorized)
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(401, "Your session has expired. Sign in again.", headers=unauthorized)
    return _public(row)


# ---------- routes ----------

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    username: str
    password: str
    full_name: str = ""


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/register", status_code=201)
def register(body: RegisterBody):
    username = body.username.strip().lower()
    full_name = body.full_name.strip()
    if not USERNAME_RE.match(username):
        raise HTTPException(
            400, "Username must be 3 to 30 characters: letters, numbers, dots, dashes or underscores."
        )
    if not 8 <= len(body.password) <= 128:
        raise HTTPException(400, "Password must be 8 to 128 characters long.")
    if len(full_name) > 60:
        raise HTTPException(400, "Name must be 60 characters or fewer.")

    try:
        with closing(_connect()) as conn, conn:
            cursor = conn.execute(
                "INSERT INTO users (username, full_name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (username, full_name, hash_password(body.password), datetime.now(timezone.utc).isoformat()),
            )
            user_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "That username is already taken. Try another one.")

    return {"access_token": create_token(user_id), "token_type": "bearer", "user": _public(row)}


@router.post("/login")
def login(body: LoginBody):
    username = body.username.strip().lower()
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    # Always run one hash check so unknown usernames take as long as wrong passwords.
    ok = verify_password(body.password, row["password_hash"] if row else _DUMMY_HASH)
    if row is None or not ok:
        raise HTTPException(401, "Incorrect username or password.")
    return {"access_token": create_token(row["id"]), "token_type": "bearer", "user": _public(row)}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user
