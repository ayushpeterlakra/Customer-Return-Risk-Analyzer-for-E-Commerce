import math
from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Customer, Order, Product, Return, RiskAssessment, RiskLevel
from app.schemas.customers import CategoryCount, CustomerDetail, CustomerListItem, OrderOut, ReturnOut
from app.schemas.risk import AssessmentOut
from app.scoring.features import is_vague
from app.services.errors import not_found
from app.services.queries import customer_overview
from app.services.scoring_service import get_active_config

SortField = Literal[
    "risk_score", "return_ratio", "total_returns", "total_orders", "last_return_date", "name", "customer_id"
]


def get_customer(db: Session, customer_id: str) -> Customer:
    customer = db.scalars(select(Customer).where(Customer.customer_id == customer_id)).first()
    if customer is None:
        raise not_found("Customer", customer_id)
    return customer


def assessment_out(customer_id: str, a: RiskAssessment) -> AssessmentOut:
    features = dict(a.features or {})
    notes = features.pop("notes", [])
    return AssessmentOut(
        customer_id=customer_id,
        risk_score=a.risk_score,
        risk_level=a.risk_level,
        risk_factors=a.risk_factors,
        requires_manual_review=a.requires_manual_review,
        scoring_method=a.scoring_method,
        config_version=a.config_version,
        notes=notes,
        features=features,
        assessed_at=a.assessed_at,
    )


def list_customers(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None,
    risk_level: RiskLevel | None,
    min_score: int | None,
    min_return_ratio: float | None,
    category: str | None,
    sort: SortField,
    order: Literal["asc", "desc"],
):
    stmt, cols = customer_overview()
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(Customer.customer_id.ilike(like), Customer.name.ilike(like)))
    if risk_level:
        stmt = stmt.where(RiskAssessment.risk_level == risk_level)
    if min_score is not None:
        stmt = stmt.where(RiskAssessment.risk_score >= min_score)
    if min_return_ratio is not None:
        stmt = stmt.where(cols["ratio"] > min_return_ratio)
    if category:
        has_cat = (
            select(Order.id)
            .join(Product, Product.id == Order.product_id)
            .where(Order.customer_id == Customer.id, Product.category == category)
            .exists()
        )
        stmt = stmt.where(has_cat)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    sort_col = {
        "risk_score": cols["risk_score"],
        "return_ratio": cols["ratio"],
        "total_returns": cols["returns"],
        "total_orders": cols["orders"],
        "last_return_date": cols["last_return_date"],
        "name": cols["name"],
        "customer_id": cols["customer_id"],
    }[sort]
    sort_expr = sort_col.desc().nulls_last() if order == "desc" else sort_col.asc().nulls_last()
    rows = db.execute(
        stmt.order_by(sort_expr, Customer.customer_id).offset((page - 1) * page_size).limit(page_size)
    )
    items = [
        CustomerListItem(
            customer_id=r.Customer.customer_id,
            name=r.Customer.name,
            total_orders=r.orders,
            total_returns=r.returns,
            return_percentage=round(float(r.ratio) * 100, 1),
            risk_score=r.RiskAssessment.risk_score if r.RiskAssessment else None,
            risk_level=r.RiskAssessment.risk_level if r.RiskAssessment else None,
            last_return_date=r.last_return_date,
            review_status=r.review_status,
        )
        for r in rows
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
    }


def customer_detail(db: Session, customer_id: str) -> CustomerDetail:
    stmt, _ = customer_overview()
    row = db.execute(stmt.where(Customer.customer_id == customer_id)).first()
    if row is None:
        raise not_found("Customer", customer_id)
    c = row.Customer
    cats = db.execute(
        select(Product.category, func.count(Order.id), func.count(Return.id))
        .join(Order, Order.product_id == Product.id)
        .outerjoin(Return, Return.order_id == Order.id)
        .where(Order.customer_id == c.id)
        .group_by(Product.category)
        .order_by(func.count(Order.id).desc())
    ).all()
    return CustomerDetail(
        customer_id=c.customer_id,
        name=c.name,
        email=c.email,
        created_at=c.created_at,
        total_orders=row.orders,
        total_returns=row.returns,
        return_percentage=round(float(row.ratio) * 100, 1),
        total_order_value=row.order_value,
        total_refunded=row.refunded,
        mismatch_count=row.mismatches,
        last_return_date=row.last_return_date,
        review_status=row.review_status,
        latest_assessment=assessment_out(c.customer_id, row.RiskAssessment) if row.RiskAssessment else None,
        categories=[CategoryCount(category=k, orders=o, returns=r) for k, o, r in cats],
    )


def customer_orders(db: Session, customer_id: str, page: int, page_size: int):
    customer = get_customer(db, customer_id)
    base = (
        select(Order, Product, Return.id.label("rid"))
        .join(Product, Product.id == Order.product_id)
        .outerjoin(Return, Return.order_id == Order.id)
        .where(Order.customer_id == customer.id)
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.order_by(Order.order_date.desc(), Order.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [
        OrderOut(
            order_id=o.order_id,
            product_id=p.product_id,
            product_name=p.product_name,
            category=p.category,
            order_date=o.order_date,
            delivery_date=o.delivery_date,
            order_amount=o.order_amount,
            order_status=o.order_status,
            customer_rating=o.customer_rating,
            returned=rid is not None,
        )
        for o, p, rid in rows
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
    }


def customer_returns(db: Session, customer_id: str, page: int, page_size: int):
    customer = get_customer(db, customer_id)
    config = get_active_config(db)
    vague_codes = set(config.vague_reason_codes)
    base = (
        select(Return, Order, Product)
        .join(Order, Order.id == Return.order_id)
        .join(Product, Product.id == Order.product_id)
        .where(Return.customer_id == customer.id)
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.order_by(Return.return_date.desc(), Return.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [
        ReturnOut(
            return_id=r.return_id,
            order_id=o.order_id,
            product_name=p.product_name,
            category=p.category,
            order_date=o.order_date,
            delivery_date=o.delivery_date,
            return_date=r.return_date,
            days_to_return=r.days_to_return,
            reason_code=r.reason_code,
            reason_text=r.reason_text,
            is_vague=is_vague(r.reason_code.value, r.reason_text, vague_codes, config.vague_text_min_length),
            mismatch_flag=r.mismatch_flag,
            refund_amount=r.refund_amount,
            return_status=r.return_status,
        )
        for r, o, p in rows
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
    }
