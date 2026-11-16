"""TAYYAR (تیار) — B2B Digital Onboarding & Tax Compliance Agency.

SQLite storage layer. No ORM, stdlib sqlite3 only.
"""
import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("TAYYAR_DB", BASE_DIR / "tayyar.db"))
UPLOAD_DIR = Path(os.environ.get("TAYYAR_UPLOADS", BASE_DIR / "uploads"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS shops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    owner_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    sector TEXT NOT NULL DEFAULT 'General Store',
    ntn TEXT DEFAULT '',
    stage TEXT NOT NULL DEFAULT 'lead',
    raast_demo_id TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER NOT NULL REFERENCES shops(id),
    doc_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS catalog_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER NOT NULL REFERENCES shops(id),
    name TEXT NOT NULL,
    price REAL NOT NULL,
    category TEXT NOT NULL DEFAULT 'General',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER NOT NULL REFERENCES shops(id),
    date TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.executescript(SCHEMA)


def row_to_dict(row):
    return dict(row) if row is not None else None
