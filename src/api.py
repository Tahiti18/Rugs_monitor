# src/api.py
import os
from typing import Dict, Any

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text

# FIX: import from src.db (not db_sql)
from src.db import get_engine, init_db

app = FastAPI(title="Rugs Monitor API", version="0.1.0")

@app.on_event("startup")
def _startup() -> None:
    db_url = os.environ["DATABASE_URL"]
    engine = get_engine(db_url)
    init_db(engine)
    app.state.engine = engine


@app.get("/", summary="Root")
def root() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "Rugs Monitor API",
        "endpoints": ["/health", "/stats/tail", "/stats/recent", "/docs"],
    }


@app.get("/health", summary="Health")
def health() -> Dict[str, bool]:
    return {"ok": True}


@app.get("/stats/tail", summary="Tail Stats")
def stats_tail() -> Dict[str, Any]:
    eng = app.state.engine
    with eng.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM rounds")).scalar_one()
        if n == 0:
            return {
                "n": 0,
                "ge2_count": 0, "ge2_freq": 0.0,
                "ge10_count": 0, "ge10_freq": 0.0,
                "ge50_count": 0, "ge50_freq": 0.0,
            }

        ge2 = conn.execute(text("SELECT COUNT(*) FROM rounds WHERE bust_multiplier >= 2.0")).scalar_one()
        ge10 = conn.execute(text("SELECT COUNT(*) FROM rounds WHERE bust_multiplier >= 10.0")).scalar_one()
        ge50 = conn.execute(text("SELECT COUNT(*) FROM rounds WHERE bust_multiplier >= 50.0")).scalar_one()

        return {
            "n": int(n),
            "ge2_count": int(ge2), "ge2_freq": float(ge2)/float(n),
            "ge10_count": int(ge10), "ge10_freq": float(ge10)/float(n),
            "ge50_count": int(ge50), "ge50_freq": float(ge50)/float(n),
        }


@app.get("/stats/recent", summary="Recent")
def stats_recent(limit: int = Query(100, ge=1, le=1000)) -> JSONResponse:
    eng = app.state.engine
    with eng.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, round_id, timestamp, bust_multiplier,
                       server_seed_hash, client_seed, nonce
                FROM rounds
                ORDER BY id DESC
                LIMIT :limit
            """),
            {"limit": limit},
        ).mappings().all()

    return JSONResponse([dict(r) for r in rows])
