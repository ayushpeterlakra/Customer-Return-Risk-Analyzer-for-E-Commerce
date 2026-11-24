"""Reusable SQL building blocks (per-customer aggregates, current review status)."""

from sqlalchemy import Select, and_, func, select
from sqlalchemy.dialects.postgresql import distinct_on

from app.models import Customer, Order, OrderStatus, Return, ReturnStatus, ReviewRecord, RiskAssessment


def order_counts():
    return (
        select(
            Order.customer_id.label("cid"),
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.order_amount), 0).label("order_value"),
        )
        .where(Order.order_status != OrderStatus.CANCELLED)
        .group_by(Order.customer_id)
        .subquery("oc")
    )


def return_counts():
    counted = Return.return_status != ReturnStatus.REJECTED
    return (
        select(
            Return.customer_id.label("cid"),
            func.count(Return.id).filter(counted).label("returns"),
            func.max(Return.return_date).label("last_return_date"),
            func.count(Return.id).filter(and_(counted, Return.mismatch_flag.is_(True))).label("mismatches"),
            func.coalesce(func.sum(Return.refund_amount), 0).label("refunded"),
        )
        .group_by(Return.customer_id)
        .subquery("rc")
    )


def current_review():
    """Latest review row per customer (DISTINCT ON is PostgreSQL's 'first row per group')."""
    return (
        select(
            ReviewRecord.customer_id.label("cid"),
            ReviewRecord.review_status.label("review_status"),
            ReviewRecord.updated_at.label("review_updated_at"),
            ReviewRecord.updated_by.label("updated_by"),
        )
        .ext(distinct_on(ReviewRecord.customer_id))
        .order_by(ReviewRecord.customer_id, ReviewRecord.updated_at.desc(), ReviewRecord.id.desc())
        .subquery("rv")
    )


def customer_overview() -> tuple[Select, dict]:
    oc, rc, rv = order_counts(), return_counts(), current_review()
    orders = func.coalesce(oc.c.orders, 0)
    returns = func.coalesce(rc.c.returns, 0)
    ratio = func.coalesce(returns * 1.0 / func.nullif(orders, 0), 0)
    cols = {
        "orders": orders,
        "returns": returns,
        "ratio": ratio,
        "last_return_date": rc.c.last_return_date,
        "risk_score": RiskAssessment.risk_score,
        "risk_level": RiskAssessment.risk_level,
        "review_status": rv.c.review_status,
        "name": Customer.name,
        "customer_id": Customer.customer_id,
    }
    stmt = (
        select(
            Customer,
            orders.label("orders"),
            returns.label("returns"),
            ratio.label("ratio"),
            rc.c.last_return_date,
            RiskAssessment,
            rv.c.review_status,
            rv.c.review_updated_at,
            func.coalesce(oc.c.order_value, 0).label("order_value"),
            func.coalesce(rc.c.refunded, 0).label("refunded"),
            func.coalesce(rc.c.mismatches, 0).label("mismatches"),
        )
        .outerjoin(oc, oc.c.cid == Customer.id)
        .outerjoin(rc, rc.c.cid == Customer.id)
        .outerjoin(RiskAssessment, RiskAssessment.id == Customer.latest_assessment_id)
        .outerjoin(rv, rv.c.cid == Customer.id)
    )
    return stmt, cols
