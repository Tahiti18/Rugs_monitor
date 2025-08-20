# src/models.py
from sqlalchemy import Column, Integer, Text, Float, DateTime
from sqlalchemy.sql import func
from src.db import Base

class Round(Base):
    __tablename__ = "rounds"

    id = Column(Integer, primary_key=True)  # SERIAL in Postgres
    round_id = Column(Text, unique=True, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    bust_multiplier = Column(Float, nullable=True)
    raw_json = Column(Text, nullable=True)
    server_seed_hash = Column(Text, nullable=True)
    client_seed = Column(Text, nullable=True)
    nonce = Column(Integer, nullable=True)
