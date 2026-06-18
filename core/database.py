import os
import sqlite3
import json
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "extractor.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT,
            file_size INTEGER,
            status TEXT NOT NULL,
            output_hash TEXT,
            error_message TEXT,
            duration_ms INTEGER,
            engine TEXT,
            depth INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signatures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            magic TEXT,
            extension TEXT,
            engine TEXT,
            count INTEGER DEFAULT 0,
            last_seen TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_operation(filename, file_type, file_size, status, output_hash=None, error_message=None, duration_ms=None, engine=None, depth=0):
    conn = get_conn()
    conn.execute(
        "INSERT INTO operations (filename, file_type, file_size, status, output_hash, error_message, duration_ms, engine, depth, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (filename, file_type, file_size, status, output_hash, error_message, duration_ms, engine, depth, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def update_signature(name, magic, extension, engine):
    conn = get_conn()
    conn.execute(
        "INSERT INTO signatures (name, magic, extension, engine, count, last_seen) VALUES (?, ?, ?, ?, 1, datetime('now')) ON CONFLICT(name) DO UPDATE SET count = count + 1, last_seen = datetime('now')",
        (name, magic, extension, engine)
    )
    conn.commit()
    conn.close()


def get_stats():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) as c FROM operations").fetchone()["c"]
    success = conn.execute("SELECT COUNT(*) as c FROM operations WHERE status='success'").fetchone()["c"]
    failed = conn.execute("SELECT COUNT(*) as c FROM operations WHERE status='failed'").fetchone()["c"]
    by_type = conn.execute("SELECT file_type, COUNT(*) as c FROM operations WHERE file_type IS NOT NULL GROUP BY file_type ORDER BY c DESC LIMIT 10").fetchall()
    recent = conn.execute("SELECT * FROM operations ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    return {
        "total": total,
        "success": success,
        "failed": failed,
        "by_type": [dict(r) for r in by_type],
        "recent": [dict(r) for r in recent]
    }


def get_summary():
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as c FROM operations").fetchone()
    conn.close()
    return row["c"] if row else 0
