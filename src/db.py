import os
import sqlite3
from contextlib import contextmanager

from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "./rugs.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id TEXT UNIQUE,
    timestamp TEXT,
    bust_multiplier REAL,
    raw_json TEXT,
    server_seed_hash TEXT,
    client_seed TEXT,
    nonce INTEGER
);
CREATE INDEX IF NOT EXISTS idx_rounds_ts ON rounds(timestamp);
CREATE INDEX IF NOT EXISTS idx_rounds_bust ON rounds(bust_multiplier);
"""

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_conn() as c:
        c.executescript(SCHEMA)
        c.commit()

def insert_round(round_id, timestamp_iso, bust_multiplier, raw_json=None,
                 server_seed_hash=None, client_seed=None, nonce=None):
    with get_conn() as c:
        c.execute(
            """
            INSERT OR IGNORE INTO rounds
            (round_id, timestamp, bust_multiplier, raw_json, server_seed_hash, client_seed, nonce)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (round_id, timestamp_iso, bust_multiplier, raw_json, server_seed_hash, client_seed, nonce),
        )
        c.commit()
