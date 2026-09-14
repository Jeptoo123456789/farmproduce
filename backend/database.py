import os
import tempfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def database_url():
    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        if configured_url.startswith("postgresql+psycopg://"):
            return configured_url
        return configured_url.replace("postgres://", "postgresql+psycopg://", 1).replace(
            "postgresql://", "postgresql+psycopg://", 1
        )

    # Vercel serverless instances are read-only except for a few writable temp areas.
    # SQLite must not be placed in the repo root for production deployments.
    temp_dir = Path(tempfile.gettempdir())
    local_database = temp_dir / "farmproduce.db"
    return f"sqlite:///{local_database}"


SQLALCHEMY_DATABASE_URL = database_url()
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
