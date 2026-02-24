import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _normalized_database_url() -> str:
    raw = os.getenv("SQLALCHEMY_DATABASE_URL", "sqlite:///./campus.db").strip()
    if not raw.startswith("sqlite"):
        return raw
    if raw.startswith("sqlite:///./"):
        relative_path = raw[len("sqlite:///./") :]
        return f"sqlite:///{(PROJECT_ROOT / relative_path).resolve()}"
    if raw.startswith("sqlite:///") and not raw.startswith("sqlite:////"):
        suffix = raw[len("sqlite:///") :]
        if suffix and not suffix.startswith("/"):
            return f"sqlite:///{(PROJECT_ROOT / suffix).resolve()}"
    return raw


SQLALCHEMY_DATABASE_URL = _normalized_database_url()
_is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
