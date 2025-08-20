from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

metadata = MetaData()

def get_engine():
    """Return the SQLAlchemy engine for database connections"""
    return engine

def init_db():
    """Initialize database (create tables if needed)"""
    from src.models import Base  # Make sure you have a models.py with Base
    Base.metadata.create_all(bind=engine)
