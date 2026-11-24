import math

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer, ReviewRecord, ReviewStatus, RiskAssessment
from app.schemas.reviews import ReviewListItem, ReviewRecordOut, ReviewUpdate
from app.services.customers_service import get_customer
from app.services.queries import current_review
from app.services.scoring_service import _current_review_status


def _out(r: ReviewRecord, customer_id: str) -> ReviewRecordOut:
    return ReviewRecordOut(
        id=r.id,
        customer_id=customer_id,
        previous_status=r.previous_status,
        review_status=r.review_status,
        review_notes=r.review_notes,
        updated_by=r.updated_by,
        updated_at=r.updated_at,
    )


def update_review(db: Session, customer_id: str, body: ReviewUpdate) -> ReviewRecordOut:
    customer = get_customer(db, customer_id)
    current = _current_review_status(db, customer.id)
    if current == body.review_status:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Review status is already {current.value}")
    record = ReviewRecord(
        customer_id=customer.id,
        previous_status=current,
        review_status=body.review_status,
        review_notes=(body.review_notes or "").strip() or None,
        updated_by=body.updated_by,
    )
    db.add(record)
    db.flush()
    db.refresh(record)
    return _out(record, customer.customer_id)


def audit_trail(db: Session, customer_id: str) -> list[ReviewRecordOut]:
    customer = get_customer(db, customer_id)
    rows = db.scalars(
        select(ReviewRecord)
        .where(ReviewRecord.customer_id == customer.id)
        .order_by(ReviewRecord.updated_at.desc(), ReviewRecord.id.desc())
    )
    return [_out(r, customer.customer_id) for r in rows]


def list_reviews(db: Session, page: int, page_size: int, review_status: ReviewStatus | None):
    rv = current_review()
    stmt = (
        select(Customer, rv.c.review_status, rv.c.updated_by, rv.c.review_updated_at, RiskAssessment)
        .join(rv, rv.c.cid == Customer.id)
        .outerjoin(RiskAssessment, RiskAssessment.id == Customer.latest_assessment_id)
    )
    if review_status:
        stmt = stmt.where(rv.c.review_status == review_status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(rv.c.review_updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = [
        ReviewListItem(
            customer_id=c.customer_id,
            name=c.name,
            review_status=s,
            updated_by=by,
            updated_at=at,
            risk_score=a.risk_score if a else None,
            risk_level=a.risk_level if a else None,
        )
        for c, s, by, at, a in rows
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
    }
