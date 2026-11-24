from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.db import session_factory


def get_tx() -> Iterator[Session]:
    """One transaction per request: commit on success, roll back on any error."""
    db = session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
