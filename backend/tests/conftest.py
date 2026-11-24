"""Shared fixtures. Integration tests need PostgreSQL; they use TEST_DATABASE_URL
(default: the return_risk_test database) and are skipped when it is unreachable."""

import os
from datetime import date

import pytest

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://rra_user:rra_password@localhost:5432/return_risk_test"
)
AS_OF = date(2026, 11, 15)


@pytest.fixture(scope="session")
def db_url():
    from sqlalchemy import create_engine, text

    try:
        with create_engine(TEST_DB_URL, connect_args={"connect_timeout": 2}).connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("Test PostgreSQL database not reachable (set TEST_DATABASE_URL)")
    return TEST_DB_URL


@pytest.fixture(scope="session")
def seeded(db_url, tmp_path_factory):
    """Fresh schema via Alembic + deterministic synthetic data, scored as of AS_OF."""
    os.environ["DATABASE_URL"] = db_url
    os.environ["SCORING_AS_OF"] = AS_OF.isoformat()
    os.environ["MODEL_DIR"] = str(tmp_path_factory.mktemp("models"))
    from alembic.config import Config

    from alembic import command
    from app.config import get_settings
    from app.db import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    from scripts.seed import seed

    labels = tmp_path_factory.mktemp("data") / "labels.csv"
    summary = seed(42, 120, AS_OF, labels_path=labels)
    yield {"summary": summary, "labels": labels}
    get_engine().dispose()


@pytest.fixture()
def client(seeded):
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
