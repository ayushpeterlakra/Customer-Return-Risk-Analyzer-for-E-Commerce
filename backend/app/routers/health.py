from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__
from app.config import get_settings
from app.db import check_database

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str  # "ok" when every dependency is reachable, otherwise "degraded"
    version: str
    environment: str
    database: str  # "ok" or "unavailable"
    database_error: str | None = None


@router.get("/health", response_model=HealthResponse, summary="Service and database health")
def health() -> HealthResponse:
    db_ok, db_error = check_database()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        version=__version__,
        environment=get_settings().app_env,
        database="ok" if db_ok else "unavailable",
        database_error=db_error,
    )
