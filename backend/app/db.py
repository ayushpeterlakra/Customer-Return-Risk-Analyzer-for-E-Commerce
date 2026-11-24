"""Database engine and session handling.

Provides the engine, a per-request session dependency, and a connectivity check
used by /api/health. Schema changes go through Alembic migrations only.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    # pool_pre_ping drops dead connections; connect_timeout keeps /api/health fast
    # when PostgreSQL is not running.
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


def session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    session = session_factory()()
    try:
        yield session
    finally:
        session.close()


def check_database() -> tuple[bool, str | None]:
    """Return (reachable, error_message)."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:  # noqa: BLE001 - report any connection failure
        return False, exc.__class__.__name__
