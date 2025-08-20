from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

def init_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS rounds (
                id SERIAL PRIMARY KEY,
                round_id TEXT UNIQUE,
                timestamp TEXT,
                bust_multiplier REAL,
                raw_json TEXT,
                server_seed_hash TEXT,
                client_seed TEXT,
                nonce INTEGER
            );
        """))
