"""SQLAlchemy ORM models — Satellite (S2.2) and Conjunction (S2.3)."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base


class Satellite(Base):
    __tablename__ = "satellites"

    catalog_no = Column(Integer, primary_key=True)
    name = Column(String(24), nullable=False)
    intl_designator = Column(String(11), nullable=True)
    line1 = Column(String(69), nullable=False)
    line2 = Column(String(69), nullable=False)
    epoch = Column(DateTime, nullable=False)
    a_km = Column(Float, nullable=True)
    ecc = Column(Float, nullable=True)
    inc_deg = Column(Float, nullable=True)
    mean_motion = Column(Float, nullable=True)
    regime = Column(String(8), nullable=True)
    group_name = Column(String(64), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Conjunction(Base):
    __tablename__ = "conjunctions"
    __table_args__ = (Index("ix_conjunctions_miss_km", "miss_km"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    sat_a = Column(Integer, ForeignKey("satellites.catalog_no"), nullable=False)
    sat_b = Column(Integer, ForeignKey("satellites.catalog_no"), nullable=False)
    tca = Column(DateTime, nullable=False)
    miss_km = Column(Float, nullable=False)
    rel_vel_kms = Column(Float, nullable=False)
    window_start = Column(DateTime, nullable=False)
    computed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    satellite_a = relationship("Satellite", foreign_keys=[sat_a])
    satellite_b = relationship("Satellite", foreign_keys=[sat_b])
