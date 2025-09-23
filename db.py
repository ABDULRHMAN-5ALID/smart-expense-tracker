# db.py
import sqlite3
from typing import List, Tuple, Optional, Dict, Any, Iterable
from datetime import datetime
from utils import DB_PATH, ensure_dirs
import hashlib

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    payment_method TEXT,
    date TEXT NOT NULL,        -- ISO: YYYY-MM-DD
    note TEXT,
    created_at TEXT NOT NULL,  -- ISO timestamp
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_date ON expenses(date);
CREATE INDEX IF NOT EXISTS idx_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_user ON expenses(user_id);
"""

def get_conn() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)

# ============= المستخدمين =============

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def create_user(username: str, password: str) -> bool:
    now = datetime.utcnow().isoformat(timespec="seconds")
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO users(username, password_hash, created_at) VALUES(?,?,?)",
                (username, hash_password(password), now)
            )
        return True
    except sqlite3.IntegrityError:
        return False  # اسم المستخدم موجود

def verify_user(username: str, password: str) -> Optional[int]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE username=?", (username,)
        ).fetchone()
        if row and row["password_hash"] == hash_password(password):
            return row["id"]
    return None

# ============= المصاريف =============

def add_expense(user_id: int, amount: float, category: str, payment_method: str,
                date_iso: str, note: str = "") -> int:
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO expenses(user_id, amount, category, payment_method, date, note, created_at)
               VALUES(?,?,?,?,?,?,?)""",
            (user_id, amount, category, payment_method, date_iso, note, now)
        )
        return cur.lastrowid

def list_expenses(user_id: int, limit: int = 50,
                  month: Optional[int] = None, year: Optional[int] = None) -> List[Dict[str, Any]]:
    q = "SELECT * FROM expenses WHERE user_id=?"
    params: Tuple[Any, ...] = (user_id,)
    where = []
    if month is not None and year is not None:
        where.append("substr(date,1,7)=?")
        params += (f"{year:04d}-{month:02d}",)
    if where:
        q += " AND " + " AND ".join(where)
    q += " ORDER BY date DESC, id DESC LIMIT ?"
    params += (limit,)
    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]

def update_expense(user_id: int, expense_id: int, fields: Dict[str, Any]) -> int:
    if not fields:
        return 0
    allowed = {"amount","category","payment_method","date","note"}
    pairs = [(k, v) for k, v in fields.items() if k in allowed]
    if not pairs:
        return 0
    set_clause = ", ".join([f"{k}=?" for k, _ in pairs])
    params = [v for _, v in pairs] + [expense_id, user_id]
    with get_conn() as conn:
        cur = conn.execute(f"UPDATE expenses SET {set_clause} WHERE id=? AND user_id=?", params)
        return cur.rowcount

def delete_expenses(user_id: int, ids: Iterable[int]) -> int:
    ids = list(ids)
    if not ids:
        return 0
    qmarks = ",".join(["?"]*len(ids))
    with get_conn() as conn:
        cur = conn.execute(f"DELETE FROM expenses WHERE id IN ({qmarks}) AND user_id=?",
                           (*ids, user_id))
        return cur.rowcount

def clear_all_expenses(user_id: int) -> int:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM expenses WHERE user_id=?", (user_id,))
        return cur.rowcount
