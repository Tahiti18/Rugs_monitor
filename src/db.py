# src/db.py
from typing import Any
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

def get_engine(db_url: str) -> Engine:
    # Pool tuned for Railway; adjust if you ever need more concurrency
    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        future=True,
    )

def init_db(engine: Engine) -> None:
    # Create table if it doesn't exist
    ddl = """
    CREATE TABLE IF NOT EXISTS rounds (
        id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        round_id TEXT UNIQUE,
        timestamp TEXT,
        bust_multiplier REAL,
        raw_json TEXT,
        server_seed_hash TEXT,
        client_seed TEXT,
        nonce INTEGER
    );
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
