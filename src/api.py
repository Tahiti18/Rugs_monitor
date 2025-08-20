# src/api.py
import os
from fastapi import FastAPI
from sqlalchemy import text
from .db_sql import get_engine, init_db

app = FastAPI(title="Rugs Monitor API", version="0.1.0")

@app.on_event("startup")
def _startup():
    init_db()

# ---- Root + Health ---------------------------------------------------------
@app.get("/")
def root():
    return {
        "ok": True,
        "service": "Rugs Monitor API",
        "endpoints": ["/health", "/stats/tail", "/stats/recent", "/docs"]
    }

@app.get("/health")
def health():
    return {"ok": True}

# ---- Stats -----------------------------------------------------------------
@app.get("/stats/tail")
def tail_stats():
    eng = get_engine()
    with eng.connect() as c:
        q = c.execute(text(
            "SELECT count(*) AS n,"
            " sum(bust_multiplier>=2.0) AS ge2,"
            " sum(bust_multiplier>=10.0) AS ge10,"
            " sum(bust_multiplier>=50.0) AS ge50"
            " FROM rounds"
        ))
        row = q.first()
    n = row.n or 0
    def freq(x): 
        return (x or 0)/n if n else 0.0
    return {
        "n": n,
        "ge2_count": int(row.ge2 or 0),  "ge2_freq": freq(row.ge2),
        "ge10_count": int(row.ge10 or 0), "ge10_freq": freq(row.ge10),
        "ge50_count": int(row.ge50 or 0), "ge50_freq": freq(row.ge50),
    }

@app.get("/stats/recent")
def recent(limit: int = 100):
    eng = get_engine()
    with eng.connect() as c:
        q = c.execute(
            text("SELECT round_id, timestamp, bust_multiplier"
                 " FROM rounds ORDER BY id DESC LIMIT :lim"),
            {"lim": limit}
        )
        rows = [dict(r) for r in q.mappings().all()]
    return rows
