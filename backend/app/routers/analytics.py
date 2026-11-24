from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_tx
from app.schemas.analytics import AnalyticsSummary, CategoryReturns, RatioBucket, ReasonCount, TrendPoint
from app.schemas.risk import LevelCount
from app.services import analytics_service as svc

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
DB = Annotated[Session, Depends(get_tx)]


def date_range(date_from: date | None = None, date_to: date | None = None) -> tuple[date | None, date | None]:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(400, "date_from must be on or before date_to")
    return date_from, date_to


Range = Annotated[tuple[date | None, date | None], Depends(date_range)]


@router.get("/summary", response_model=AnalyticsSummary)
def summary(db: DB, rng: Range):
    return svc.summary(db, *rng)


@router.get("/returns-by-category", response_model=list[CategoryReturns])
def returns_by_category(db: DB, rng: Range):
    return svc.returns_by_category(db, *rng)


@router.get("/risk-distribution", response_model=list[LevelCount])
def risk_distribution(db: DB):
    return svc.risk_distribution(db)


@router.get("/return-trends", response_model=list[TrendPoint])
def return_trends(db: DB, rng: Range, granularity: Annotated[Literal["day", "week"], Query()] = "week"):
    return svc.return_trends(db, granularity, *rng)


@router.get("/return-ratio-distribution", response_model=list[RatioBucket])
def return_ratio_distribution(db: DB):
    return svc.return_ratio_distribution(db)


@router.get("/return-reasons", response_model=list[ReasonCount])
def return_reasons(db: DB, rng: Range):
    return svc.reasons_breakdown(db, *rng)
