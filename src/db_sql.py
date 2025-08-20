# src/db_sql.py
from sqlalchemy import create_engine, text

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS rounds (
  id SERIAL PRIMARY KEY,
  round_id TEXT UNIQUE,
  timestamp TIMESTAMPTZ,
  bust_multiplier DOUBLE PRECISION,
  raw_json TEXT,
  server_seed_hash TEXT,
  client_seed TEXT,
  nonce INTEGER
);
"""

def get_engine(database_url: str):
    # pool_pre_ping avoids stale connections
    return create_engine(database_url, pool_pre_ping=True)

def init_db(engine) -> None:
    # Create schema if it doesn't exist
    with engine.begin() as conn:
        conn.execute(text(SCHEMA_SQL))
      
