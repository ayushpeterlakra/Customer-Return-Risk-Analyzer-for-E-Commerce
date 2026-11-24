import math
import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer, ReviewStatus, RiskAssessment, RiskLevel
from app.schemas.risk import AssessmentHistoryItem, HighRiskItem, RiskSummary
from app.services.customers_service import assessment_out, get_customer
from app.services.errors import not_found
from app.services.queries import current_review
from app.services.scoring_service import assess_all, assess_customers


def assess_one(db: Session, customer_id: str):
    customer = get_customer(db, customer_id)
    [assessment] = assess_customers(db, [customer])
    return assessment_out(customer.customer_id, assessment)


def assess_everyone(db: Session) -> dict:
    start = time.perf_counter()
    result = assess_all(db)
    return {**result, "duration_ms": int((time.perf_counter() - start) * 1000)}


def latest(db: Session, customer_id: str):
    customer = get_customer(db, customer_id)
    if customer.latest_assessment is None:
        raise not_found("Risk assessment for customer", customer_id)
    return assessment_out(customer.customer_id, customer.latest_assessment)


def history(db: Session, customer_id: str, limit: int) -> list[AssessmentHistoryItem]:
    customer = get_customer(db, customer_id)
    rows = db.scalars(
        select(RiskAssessment)
        .where(RiskAssessment.customer_id == customer.id)
        .order_by(RiskAssessment.assessed_at.desc(), RiskAssessment.id.desc())
        .limit(limit)
    )
    items = [
        AssessmentHistoryItem(
            risk_score=a.risk_score,
            risk_level=a.risk_level,
            config_version=a.config_version,
            assessed_at=a.assessed_at,
        )
        for a in rows
    ]
    return list(reversed(items))


def high_risk(db: Session, page: int, page_size: int, review_status: ReviewStatus | None):
    rv = current_review()
    stmt = (
        select(Customer, RiskAssessment, rv.c.review_status, rv.c.review_updated_at)
        .join(RiskAssessment, RiskAssessment.id == Customer.latest_assessment_id)
        .outerjoin(rv, rv.c.cid == Customer.id)
        .where(RiskAssessment.risk_level == RiskLevel.HIGH)
    )
    if review_status:
        stmt = stmt.where(rv.c.review_status == review_status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(RiskAssessment.risk_score.desc(), Customer.customer_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [
        HighRiskItem(
            customer_id=c.customer_id,
            name=c.name,
            risk_score=a.risk_score,
            risk_level=a.risk_level,
            top_factors=a.risk_factors[:3],
            review_status=status,
            review_updated_at=updated,
            assessed_at=a.assessed_at,
        )
        for c, a, status, updated in rows
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
    }


def summary(db: Session) -> RiskSummary:
    rows = dict(
        db.execute(
            select(RiskAssessment.risk_level, func.count())
            .join(Customer, Customer.latest_assessment_id == RiskAssessment.id)
            .group_by(RiskAssessment.risk_level)
        ).all()
    )
    total = sum(rows.values())
    avg = (
        db.scalar(
            select(func.avg(RiskAssessment.risk_score)).join(
                Customer, Customer.latest_assessment_id == RiskAssessment.id
            )
        )
        or 0
    )
    review = (
        db.scalar(
            select(func.count())
            .select_from(RiskAssessment)
            .join(Customer, Customer.latest_assessment_id == RiskAssessment.id)
            .where(RiskAssessment.requires_manual_review.is_(True))
        )
        or 0
    )
    return RiskSummary(
        total_assessed=total,
        levels=[
            {
                "risk_level": lvl,
                "count": rows.get(lvl, 0),
                "percentage": round(rows.get(lvl, 0) * 100 / total, 1) if total else 0.0,
            }
            for lvl in RiskLevel
        ],
        average_score=round(float(avg), 1),
        requires_review=review,
    )
