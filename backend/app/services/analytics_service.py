from datetime import date, timedelta

from sqlalchemy import Date, and_, case, cast, func, select
from sqlalchemy.orm import Session

from app.models import Customer, Order, OrderStatus, Product, Return, ReturnStatus, RiskAssessment, RiskLevel
from app.schemas.analytics import AnalyticsSummary, CategoryReturns, RatioBucket, ReasonCount, TrendPoint
from app.services.queries import order_counts, return_counts
from app.services.scoring_service import get_active_config


def _range(col, date_from: date | None, date_to: date | None):
    conds = []
    if date_from:
        conds.append(col >= date_from)
    if date_to:
        conds.append(col <= date_to)
    return and_(True, *conds)


def summary(db: Session, date_from: date | None, date_to: date | None) -> AnalyticsSummary:
    orders_q = select(func.count(Order.id)).where(
        Order.order_status != OrderStatus.CANCELLED, _range(Order.order_date, date_from, date_to)
    )
    returns_q = select(func.count(Return.id), func.coalesce(func.sum(Return.refund_amount), 0)).where(
        Return.return_status != ReturnStatus.REJECTED, _range(Return.return_date, date_from, date_to)
    )
    total_returns, refunded = db.execute(returns_q).one()
    oc, rc = order_counts(), return_counts()
    # Average of per-customer return ratios over customers with at least one order (all-time).
    avg_ratio = (
        db.scalar(
            select(func.avg(func.coalesce(rc.c.returns, 0) * 1.0 / oc.c.orders))
            .select_from(oc)
            .outerjoin(rc, rc.c.cid == oc.c.cid)
        )
        or 0
    )
    levels = dict(
        db.execute(
            select(RiskAssessment.risk_level, func.count())
            .join(Customer, Customer.latest_assessment_id == RiskAssessment.id)
            .group_by(RiskAssessment.risk_level)
        ).all()
    )
    return AnalyticsSummary(
        total_customers=db.scalar(select(func.count(Customer.id))) or 0,
        total_orders=db.scalar(orders_q) or 0,
        total_returns=total_returns,
        average_return_ratio=round(float(avg_ratio), 4),
        high_risk_customers=levels.get(RiskLevel.HIGH, 0),
        medium_risk_customers=levels.get(RiskLevel.MEDIUM, 0),
        low_risk_customers=levels.get(RiskLevel.LOW, 0),
        total_refunded=float(refunded),
        date_from=date_from,
        date_to=date_to,
    )


def returns_by_category(db: Session, date_from: date | None, date_to: date | None) -> list[CategoryReturns]:
    orders = dict(
        db.execute(
            select(Product.category, func.count(Order.id))
            .join(Order, Order.product_id == Product.id)
            .where(Order.order_status == OrderStatus.DELIVERED, _range(Order.order_date, date_from, date_to))
            .group_by(Product.category)
        ).all()
    )
    rows = db.execute(
        select(
            Product.category,
            func.count(Return.id),
            func.count(Return.id).filter(Return.mismatch_flag.is_(True)),
        )
        .join(Order, Order.product_id == Product.id)
        .join(Return, Return.order_id == Order.id)
        .where(Return.return_status != ReturnStatus.REJECTED, _range(Return.return_date, date_from, date_to))
        .group_by(Product.category)
    ).all()
    returns = {cat: (n, m) for cat, n, m in rows}
    cats = sorted(set(orders) | set(returns))
    out = [
        CategoryReturns(
            category=c,
            orders=orders.get(c, 0),
            returns=returns.get(c, (0, 0))[0],
            return_rate=round(returns.get(c, (0, 0))[0] / orders[c], 4) if orders.get(c) else 0,
            mismatches=returns.get(c, (0, 0))[1],
        )
        for c in cats
    ]
    return sorted(out, key=lambda x: -x.returns)


def risk_distribution(db: Session):
    rows = dict(
        db.execute(
            select(RiskAssessment.risk_level, func.count())
            .join(Customer, Customer.latest_assessment_id == RiskAssessment.id)
            .group_by(RiskAssessment.risk_level)
        ).all()
    )
    total = sum(rows.values())
    return [
        {
            "risk_level": lvl,
            "count": rows.get(lvl, 0),
            "percentage": round(rows.get(lvl, 0) * 100 / total, 1) if total else 0.0,
        }
        for lvl in RiskLevel
    ]


def return_trends(
    db: Session, granularity: str, date_from: date | None, date_to: date | None
) -> list[TrendPoint]:
    unit = "week" if granularity == "week" else "day"
    r_period = cast(func.date_trunc(unit, Return.return_date), Date)
    o_period = cast(func.date_trunc(unit, Order.order_date), Date)
    rets = {
        p: (n, m)
        for p, n, m in db.execute(
            select(
                r_period, func.count(Return.id), func.count(Return.id).filter(Return.mismatch_flag.is_(True))
            )
            .where(
                Return.return_status != ReturnStatus.REJECTED, _range(Return.return_date, date_from, date_to)
            )
            .group_by(r_period)
        ).all()
    }
    ords = dict(
        db.execute(
            select(o_period, func.count(Order.id))
            .where(Order.order_status != OrderStatus.CANCELLED, _range(Order.order_date, date_from, date_to))
            .group_by(o_period)
        ).all()
    )
    periods = sorted(set(rets) | set(ords))
    if not periods:
        return []
    # Fill gaps so the line chart shows zero periods instead of skipping them.
    step = timedelta(days=7 if unit == "week" else 1)
    filled, current = [], periods[0]
    while current <= periods[-1]:
        n, m = rets.get(current, (0, 0))
        filled.append(TrendPoint(period_start=current, returns=n, orders=ords.get(current, 0), mismatches=m))
        current += step
    return filled


def return_ratio_distribution(db: Session) -> list[RatioBucket]:
    oc, rc = order_counts(), return_counts()
    ratio = func.least(func.coalesce(rc.c.returns, 0) * 1.0 / oc.c.orders, 1.0)
    bucket = func.least(func.floor(ratio * 10), 9)
    counts = dict(
        db.execute(
            select(bucket, func.count()).select_from(oc).outerjoin(rc, rc.c.cid == oc.c.cid).group_by(bucket)
        ).all()
    )
    return [
        RatioBucket(
            bucket=f"{i * 10}-{i * 10 + 10}%",
            lower=i / 10,
            upper=(i + 1) / 10,
            customers=int(counts.get(i, 0)),
        )
        for i in range(10)
    ]


def reasons_breakdown(db: Session, date_from: date | None, date_to: date | None) -> list[ReasonCount]:
    config = get_active_config(db)
    vague = and_(
        Return.reason_code.in_(config.vague_reason_codes),
        func.length(func.trim(func.coalesce(Return.reason_text, ""))) < config.vague_text_min_length,
    )
    rows = db.execute(
        select(Return.reason_code, func.count(Return.id), func.sum(case((vague, 1), else_=0)))
        .where(Return.return_status != ReturnStatus.REJECTED, _range(Return.return_date, date_from, date_to))
        .group_by(Return.reason_code)
        .order_by(func.count(Return.id).desc())
    ).all()
    return [ReasonCount(reason_code=code.value, count=n, vague=int(v or 0)) for code, n, v in rows]
