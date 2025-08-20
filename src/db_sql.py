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
