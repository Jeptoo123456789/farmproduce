import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def database_url():
    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        return configured_url.replace("postgres://", "postgresql+psycopg://", 1)
    local_database = Path(__file__).resolve().parents[1] / "farmproduce.db"
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
