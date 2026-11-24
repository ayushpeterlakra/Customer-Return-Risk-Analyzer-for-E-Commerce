from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.deps import get_tx
from app.models import ReviewStatus
from app.schemas.common import Page
from app.schemas.risk import AssessAllResult, AssessmentHistoryItem, AssessmentOut, HighRiskItem, RiskSummary
from app.services import risk_service as svc

router = APIRouter(prefix="/api/risk", tags=["risk"])
DB = Annotated[Session, Depends(get_tx)]


@router.post("/assess-all", response_model=AssessAllResult, summary="Rescore every customer")
def assess_all(db: DB):
    return svc.assess_everyone(db)


@router.get("/high-risk", response_model=Page[HighRiskItem], summary="High-risk customers for monitoring")
def high_risk(
    db: DB,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    review_status: ReviewStatus | None = None,
):
    return svc.high_risk(db, page, page_size, review_status)


@router.get("/summary", response_model=RiskSummary, summary="Counts by risk level")
def summary(db: DB):
    return svc.summary(db)


@router.post(
    "/assess/{customer_id}",
    response_model=AssessmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Score one customer now",
)
def assess(customer_id: str, db: DB):
    return svc.assess_one(db, customer_id)


@router.get("/{customer_id}", response_model=AssessmentOut, summary="Latest assessment")
def latest(customer_id: str, db: DB):
    return svc.latest(db, customer_id)


@router.get("/{customer_id}/history", response_model=list[AssessmentHistoryItem], summary="Score history")
def history(customer_id: str, db: DB, limit: Annotated[int, Query(ge=1, le=500)] = 100):
    return svc.history(db, customer_id, limit)
