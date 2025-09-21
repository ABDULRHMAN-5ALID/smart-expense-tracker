# utils.py
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "expenses.db"

def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
