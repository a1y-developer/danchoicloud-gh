from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_path(database_url: str) -> None:
    if not database_url.startswith("sqlite"):
        return
    path = database_url.replace("sqlite:///", "", 1)
    if not path or path == ":memory:":
        return
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _build_database_url() -> str:
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    local_path = Path(settings.LOCAL_DB_PATH)
    if not local_path.is_absolute():
        local_path = Path.cwd() / local_path
    return f"sqlite:///{local_path}"


def _build_engine():
    database_url = _build_database_url()
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    _ensure_sqlite_path(database_url)
    return create_engine(database_url, connect_args=connect_args, future=True)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_session() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
