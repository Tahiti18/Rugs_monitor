import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_PATH = os.getenv("DB_PATH", "./rugs.db")

def get_engine() -> Engine:
    if DATABASE_URL:
        return create_engine(DATABASE_URL, pool_pre_ping=True)
    else:
        return create_engine(f"sqlite:///{DB_PATH}", pool_pre_ping=True)

SCHEMA = '''
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
'''

def init_db():
    eng = get_engine()
    with eng.begin() as conn:
        for stmt in SCHEMA.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
