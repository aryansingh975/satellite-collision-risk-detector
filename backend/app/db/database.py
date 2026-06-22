"""SQLAlchemy engine, session factory, declarative base, and DB helpers — S2.1."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables registered on Base.metadata.

    Call this after importing all ORM model modules so every table is registered
    before create_all runs. Safe to call multiple times (idempotent).
    """
    Base.metadata.create_all(bind=engine)
