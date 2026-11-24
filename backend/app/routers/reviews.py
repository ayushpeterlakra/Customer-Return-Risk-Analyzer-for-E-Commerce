from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_tx
from app.models import ReviewStatus
from app.schemas.common import Page
from app.schemas.reviews import ReviewListItem, ReviewRecordOut, ReviewUpdate
from app.services import reviews_service as svc

router = APIRouter(prefix="/api/reviews", tags=["reviews"])
DB = Annotated[Session, Depends(get_tx)]


@router.patch(
    "/{customer_id}", response_model=ReviewRecordOut, summary="Change review status (adds audit row)"
)
def update_review(customer_id: str, body: ReviewUpdate, db: DB):
    return svc.update_review(db, customer_id, body)


@router.get("", response_model=Page[ReviewListItem], summary="Current review status per customer")
def list_reviews(
    db: DB,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    review_status: ReviewStatus | None = None,
):
    return svc.list_reviews(db, page, page_size, review_status)


@router.get("/{customer_id}", response_model=list[ReviewRecordOut], summary="Audit trail, newest first")
def audit_trail(customer_id: str, db: DB):
    return svc.audit_trail(db, customer_id)
