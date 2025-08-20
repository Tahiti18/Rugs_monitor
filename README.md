# rugs_monitor

Purpose: log crash-game rounds, store them, run statistical tests for independence and distribution fit, and backtest baseline strategies to demonstrate expected EV. This is **for research only** and may violate a site's ToS. Use at your own risk.

## Quick Start

1) Python 3.11 recommended.
2) Install dependencies:
```bash
pip install -r requirements.txt
python -m playwright install
```
3) Copy `.env.example` to `.env` and set values.
4) Run the scraper to build a dataset:
```bash
python src/scraper.py
```
5) Analyze statistics and independence:
```bash
python src/analyze.py
```
6) Run baseline backtests:
```bash
python src/backtest.py
```

## Data Model

Table: `rounds`
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `round_id` TEXT UNIQUE
- `timestamp` TEXT (ISO 8601 UTC)
- `bust_multiplier` REAL
- `raw_json` TEXT (nullable)
- `server_seed_hash` TEXT (nullable)
- `client_seed` TEXT (nullable)
- `nonce` INTEGER (nullable)

Indices:
- `idx_rounds_ts` on `timestamp`
- `idx_rounds_bust` on `bust_multiplier`

## What This Does (and Does Not)
- **Does**: log public round data by watching DOM changes and intercepting network requests; persist to SQLite; run independence tests (runs test, autocorrelation), distribution checks (ECDF vs. empirical), and basic anomaly flags.
- **Does Not**: guarantee profit, predict future rounds, or bypass any house edge. It is intended to *detect flaws*. If the stream is truly random and house-edged, expected value remains negative.

## Legal & Ethical
- Scraping or automating gameplay likely violates terms of service. Operating bots can get accounts banned or worse. This code is for learning and audits only.

---

## Deploy on Railway (API + Scraper)

**Services (recommended):**
- **API service** (uses Dockerfile default command): exposes `/health`, `/stats/*`
- **Scraper service** (same repo) with start command override: `python src/scraper_ws.py`

**Steps:**
1) Push to GitHub.
2) In Railway, "New Project" → "Deploy from Repo".
3) Add a **Postgres** plugin (or set `DATABASE_URL` to your own). If you skip Postgres, it will use SQLite (not recommended for production).
4) Create **Service A (API)**: default Dockerfile start command.
5) Create **Service B (SCRAPER)**: override start command to `python src/scraper_ws.py`.
6) Set env vars on both:
   - `TARGET_URL=https://rugs.fun`
   - `HEADLESS=true`
   - `DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DBNAME` (Railway will provide)
7) Confirm health at `/health` on the API service.

## Deploy Dashboard on Netlify

- Drag-drop `dashboard/` folder or connect repo and set publish dir to `dashboard`.
- In the dashboard URL, pass `?api=https://<railway-api-domain>/` if Netlify is on a different domain.

Example: `https://your-netlify-app.netlify.app/?api=https://your-railway-api.up.railway.app/`

## Notes

- The scraper uses **WebSocket frame sniffing** and **XHR intercept**. First run will log a lot of frames; tighten parsing inside `handle_payload()` once you observe the site’s real payload structure.
- If the site exposes provably-fair artifacts (seed hash, nonce), extend `store_round()` schema and persist them for later verification.
