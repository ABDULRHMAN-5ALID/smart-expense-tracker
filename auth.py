import sqlite3
import hashlib
from utils import DB_PATH, ensure_dirs

SCHEMA_AUTH = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

def get_conn():
    ensure_dirs()
    return sqlite3.connect(DB_PATH)

def init_auth():
    with get_conn() as conn:
        conn.execute(SCHEMA_AUTH)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def create_user(username: str, password: str) -> bool:
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO users(username, password_hash, created_at) VALUES (?,?,datetime('now'))",
                (username, hash_password(password))
            )
        return True
    except sqlite3.IntegrityError:
        return False  # username موجود مسبقاً

def validate_user(username: str, password: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username=?",
            (username,)
        ).fetchone()
        if not row:
            return False
        return row[0] == hash_password(password)
