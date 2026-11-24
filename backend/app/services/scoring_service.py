"""Bridges the database and the pure scoring engine."""

import logging
from collections import defaultdict
from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Customer,
    Order,
    OrderStatus,
    Product,
    Return,
    ReturnStatus,
    ReviewRecord,
    ReviewStatus,
    RiskAssessment,
    RiskLevel,
    ScoringConfigRecord,
    ScoringMethod,
)
from app.scoring import (
    OrderRecord,
    ReturnRecord,
    ScoringConfig,
    compute_features,
    load_default_config,
    score_customer,
)
from app.services.notifications import notify_new_high_risk

logger = logging.getLogger(__name__)


def scoring_date() -> date:
    return get_settings().scoring_as_of or date.today()


def get_active_config(db: Session) -> ScoringConfig:
    record = db.scalars(select(ScoringConfigRecord).order_by(ScoringConfigRecord.id.desc()).limit(1)).first()
    return ScoringConfig.model_validate(record.config) if record else load_default_config()


def recompute_category_risk(db: Session) -> dict[str, float]:
    """Set products.category_risk to each category's observed return rate on delivered orders."""
    delivered = dict(
        db.execute(
            select(Product.category, func.count(Order.id))
            .join(Order, Order.product_id == Product.id)
            .where(Order.order_status == OrderStatus.DELIVERED)
            .group_by(Product.category)
        ).all()
    )
    returned = dict(
        db.execute(
            select(Product.category, func.count(Return.id))
            .join(Order, Order.product_id == Product.id)
            .join(Return, Return.order_id == Order.id)
            .group_by(Product.category)
        ).all()
    )
    rates = {cat: round(returned.get(cat, 0) / n, 3) for cat, n in delivered.items() if n}
    for cat, rate in rates.items():
        db.execute(update(Product).where(Product.category == cat).values(category_risk=rate))
    return rates


def high_risk_categories(db: Session, config: ScoringConfig) -> set[str]:
    delivered = (
        db.scalar(select(func.count(Order.id)).where(Order.order_status == OrderStatus.DELIVERED)) or 0
    )
    returns = db.scalar(select(func.count(Return.id))) or 0
    if delivered == 0:
        return set()
    store_rate = returns / delivered
    rows = db.execute(
        select(Product.category, func.max(Product.category_risk)).group_by(Product.category)
    ).all()
    return {cat for cat, risk in rows if float(risk) > store_rate + config.high_return_category_margin}


def _records_for(db: Session, customer_ids: list[int] | None = None):
    order_q = select(
        Order.customer_id, Order.order_date, Order.order_status, Product.category, Order.customer_rating
    ).join(Product, Product.id == Order.product_id)
    return_q = (
        select(
            Return.customer_id,
            Return.return_date,
            Return.days_to_return,
            Return.reason_code,
            Return.reason_text,
            Return.mismatch_flag,
            Return.return_status,
            Product.category,
            Order.customer_rating,
            Order.delivery_date,
        )
        .join(Order, Order.id == Return.order_id)
        .join(Product, Product.id == Order.product_id)
    )
    if customer_ids is not None:
        order_q = order_q.where(Order.customer_id.in_(customer_ids))
        return_q = return_q.where(Return.customer_id.in_(customer_ids))
    orders: dict[int, list[OrderRecord]] = defaultdict(list)
    returns: dict[int, list[ReturnRecord]] = defaultdict(list)
    for cid, odate, status, cat, rating in db.execute(order_q):
        orders[cid].append(OrderRecord(odate, status.value, cat, rating))
    for cid, rdate, days, code, text, mismatch, status, cat, rating, delivery in db.execute(return_q):
        # days_to_return is None when the order has no delivery date (data issue).
        window = days if delivery is not None else None
        returns[cid].append(
            ReturnRecord(rdate, window, code.value, text, mismatch, status.value, cat, rating)
        )
    return orders, returns


def _current_review_status(db: Session, customer_pk: int) -> ReviewStatus | None:
    return db.scalars(
        select(ReviewRecord.review_status)
        .where(ReviewRecord.customer_id == customer_pk)
        .order_by(ReviewRecord.updated_at.desc(), ReviewRecord.id.desc())
        .limit(1)
    ).first()


def _save(
    db: Session, customer: Customer, result, features, previous_level: RiskLevel | None
) -> RiskAssessment:
    assessment = RiskAssessment(
        customer_id=customer.id,
        risk_score=result.risk_score,
        risk_level=RiskLevel(result.risk_level),
        scoring_method=ScoringMethod.RULE_BASED,
        config_version=result.config_version,
        risk_factors=result.factors_as_dicts(),
        features={**features.to_dict(), "notes": result.notes},
        requires_manual_review=result.requires_manual_review,
    )
    db.add(assessment)
    db.flush()
    customer.latest_assessment_id = assessment.id
    if result.risk_level == "HIGH" and previous_level != RiskLevel.HIGH:
        if _current_review_status(db, customer.id) is None:
            db.add(
                ReviewRecord(
                    customer_id=customer.id,
                    previous_status=None,
                    review_status=ReviewStatus.PENDING_REVIEW,
                    review_notes="Automatically queued: risk level became HIGH.",
                    updated_by="system",
                )
            )
        notify_new_high_risk(customer.customer_id, result.risk_score)
    return assessment


def assess_customers(db: Session, customers: list[Customer]) -> list[RiskAssessment]:
    config = get_active_config(db)
    categories = high_risk_categories(db, config)
    as_of = scoring_date()
    ids = [c.id for c in customers]
    orders, returns = _records_for(db, ids)
    previous = dict(
        db.execute(
            select(Customer.id, RiskAssessment.risk_level)
            .join(RiskAssessment, RiskAssessment.id == Customer.latest_assessment_id)
            .where(Customer.id.in_(ids))
        ).all()
    )
    saved = []
    for customer in customers:
        features = compute_features(
            orders.get(customer.id, []),
            returns.get(customer.id, []),
            as_of=as_of,
            vague_codes=set(config.vague_reason_codes),
            vague_text_min_length=config.vague_text_min_length,
            high_risk_categories=categories,
        )
        result = score_customer(features, config)
        saved.append(_save(db, customer, result, features, previous.get(customer.id)))
    return saved


def assess_all(db: Session) -> dict[str, int]:
    customers = list(db.scalars(select(Customer).order_by(Customer.id)))
    saved = assess_customers(db, customers)
    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for a in saved:
        counts[a.risk_level.value] += 1
    return {"assessed": len(saved), **counts}


def features_for_customers(db: Session, customers: list[Customer] | None = None) -> dict[int, dict]:
    """Feature dicts per customer pk, used by the ML pipeline."""
    config = get_active_config(db)
    categories = high_risk_categories(db, config)
    customers = customers if customers is not None else list(db.scalars(select(Customer)))
    orders, returns = _records_for(db, [c.id for c in customers])
    out = {}
    for c in customers:
        f = compute_features(
            orders.get(c.id, []),
            returns.get(c.id, []),
            as_of=scoring_date(),
            vague_codes=set(config.vague_reason_codes),
            vague_text_min_length=config.vague_text_min_length,
            high_risk_categories=categories,
        )
        out[c.id] = f.to_dict()
    return out


__all__ = ["ReturnStatus", "assess_all", "assess_customers", "get_active_config", "recompute_category_risk"]
