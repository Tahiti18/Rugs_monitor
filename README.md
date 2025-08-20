# Rugs Backend (Clean, Postgres-ready)

**What this is:** A minimal FastAPI + SQLAlchemy backend, configured for **Postgres** (Railway). No SQLite leftovers.

## Files
- `requirements.txt` — dependencies
- `Procfile` — tells Railway to run: `uvicorn src.api:app --host 0.0.0.0 --port 8080`
- `src/db.py` — engine + metadata + init_db()
- `src/models.py` — Round table (id SERIAL, timestamp timestamptz, float bust)
- `src/api.py` — endpoints: `/`, `/health`, `/stats/tail`, `/stats/recent`

## Deploy (Railway)
1. Create a project → connect this repo/zip.
2. Set **Variables** on the web service:
   - `DATABASE_URL=postgresql://<user>:<pass>@<host>:<port>/<db>?sslmode=require` (use your Postgres public proxy)
3. Deploy. Visit `/health` to check.

> If `/stats/*` are empty, start your scraper service separately; this API doesn’t fetch data on its own.
