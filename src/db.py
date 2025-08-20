# src/db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

def get_engine(database_url: str | None = None):
    if database_url is None:
        database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    # future=True for 2.0 style, pool_pre_ping avoids stale sockets
    return create_engine(database_url, pool_pre_ping=True, future=True)

def init_db(engine):
    # Import models to register metadata, then create tables
    from src import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
