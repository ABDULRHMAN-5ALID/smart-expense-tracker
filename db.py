# db.py
import sqlite3
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
from utils import DB_PATH, ensure_dirs

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    payment_method TEXT,
    date TEXT NOT NULL,        -- ISO: YYYY-MM-DD
    note TEXT,
    created_at TEXT NOT NULL   -- ISO timestamp
);

CREATE INDEX IF NOT EXISTS idx_date ON expenses(date);
CREATE INDEX IF NOT EXISTS idx_category ON expenses(category);
"""

def get_conn() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)

def add_expense(amount: float, category: str, payment_method: str,
                date_iso: str, note: str = "") -> int:
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO expenses(amount, category, payment_method, date, note, created_at)
               VALUES(?,?,?,?,?,?)""",
            (amount, category, payment_method, date_iso, note, now)
        )
        return cur.lastrowid

def list_expenses(limit: int = 50, month: Optional[int] = None, year: Optional[int] = None) -> List[Dict[str, Any]]:
    q = "SELECT * FROM expenses"
    params: Tuple[Any, ...] = tuple()
    where = []
    if month is not None and year is not None:
        where.append("substr(date,1,7)=?")
        params += (f"{year:04d}-{month:02d}",)
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY date DESC, id DESC LIMIT ?"
    params += (limit,)
    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]
# db.py — أضف الدوال التالية
from typing import Optional, Dict, Any, Iterable
from utils import DB_PATH, ensure_dirs
import sqlite3
from datetime import datetime

def update_expense(expense_id: int, fields: Dict[str, Any]) -> int:
    """
    يحدّث الأعمدة المعطاة فقط. مثال fields={"amount": 50, "note":"..."}
    """
    if not fields:
        return 0
    allowed = {"amount","category","payment_method","date","note"}
    pairs = [(k, v) for k, v in fields.items() if k in allowed]
    if not pairs:
        return 0
    set_clause = ", ".join([f"{k}=?" for k, _ in pairs])
    params = [v for _, v in pairs] + [expense_id]
    with get_conn() as conn:
        cur = conn.execute(f"UPDATE expenses SET {set_clause} WHERE id=?", params)
        return cur.rowcount

def delete_expenses(ids: Iterable[int]) -> int:
    ids = list(ids)
    if not ids:
        return 0
    qmarks = ",".join(["?"]*len(ids))
    with get_conn() as conn:
        cur = conn.execute(f"DELETE FROM expenses WHERE id IN ({qmarks})", ids)
        return cur.rowcount
