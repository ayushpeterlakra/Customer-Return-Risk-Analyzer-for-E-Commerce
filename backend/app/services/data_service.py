"""CSV import (all-or-nothing) and flagged-customer export."""

import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    Order,
    OrderStatus,
    Product,
    ReasonCode,
    Return,
    ReturnStatus,
    RiskAssessment,
    RiskLevel,
)
from app.services.queries import customer_overview
from app.services.scoring_service import assess_all, recompute_category_risk

IMPORT_COLUMNS = [
    "customer_id",
    "customer_name",
    "customer_email",
    "order_id",
    "product_id",
    "product_name",
    "category",
    "order_date",
    "delivery_date",
    "order_amount",
    "order_status",
    "customer_rating",
    "return_id",
    "reason_code",
    "reason_text",
    "return_date",
    "mismatch_flag",
    "refund_amount",
    "return_status",
]
MAX_ROWS = 20000


@dataclass
class Row:
    line: int
    data: dict[str, str]


def _parse_date(v: str, field: str, errors: list, line: int, required=True) -> date | None:
    if not v:
        if required:
            errors.append({"line": line, "field": field, "message": "is required"})
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        errors.append({"line": line, "field": field, "message": f"'{v}' is not a YYYY-MM-DD date"})
        return None


def _parse_money(v: str, field: str, errors: list, line: int) -> Decimal | None:
    try:
        d = Decimal(v)
        if d < 0:
            raise InvalidOperation
        return d
    except (InvalidOperation, ValueError):
        errors.append({"line": line, "field": field, "message": f"'{v}' is not a non-negative amount"})
        return None


def _enum(cls, v: str, field: str, errors: list, line: int):
    try:
        return cls(v.strip().upper())
    except ValueError:
        errors.append(
            {
                "line": line,
                "field": field,
                "message": f"'{v}' must be one of {', '.join(m.value for m in cls)}",
            }
        )
        return None


def import_csv(db: Session, content: bytes) -> dict:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must be UTF-8 encoded CSV") from exc
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in IMPORT_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Missing columns: {', '.join(missing)}")
    rows = [Row(i + 2, {k: (v or "").strip() for k, v in r.items() if k}) for i, r in enumerate(reader)]
    if not rows:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The file has no data rows")
    if len(rows) > MAX_ROWS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"At most {MAX_ROWS} rows per import")

    errors: list[dict] = []
    existing_orders = set(db.scalars(select(Order.order_id)))
    existing_returns = set(db.scalars(select(Return.return_id)))
    customers = {c.customer_id: c for c in db.scalars(select(Customer))}
    products = {p.product_id: p for p in db.scalars(select(Product))}
    seen_orders: set[str] = set()
    parsed = []
    for row in rows:
        d, line = row.data, row.line
        for f in (
            "customer_id",
            "customer_name",
            "customer_email",
            "order_id",
            "product_id",
            "product_name",
            "category",
            "order_amount",
            "order_status",
        ):
            if not d.get(f):
                errors.append({"line": line, "field": f, "message": "is required"})
        if d.get("order_id") in existing_orders or d.get("order_id") in seen_orders:
            errors.append(
                {"line": line, "field": "order_id", "message": f"duplicate order_id {d.get('order_id')}"}
            )
        seen_orders.add(d.get("order_id", ""))
        existing = customers.get(d.get("customer_id", ""))
        if existing and existing.email != d.get("customer_email"):
            errors.append(
                {
                    "line": line,
                    "field": "customer_email",
                    "message": "does not match the existing customer's email",
                }
            )
        order_date = _parse_date(d.get("order_date", ""), "order_date", errors, line)
        delivery = _parse_date(d.get("delivery_date", ""), "delivery_date", errors, line, required=False)
        amount = (
            _parse_money(d.get("order_amount", ""), "order_amount", errors, line)
            if d.get("order_amount")
            else None
        )
        order_status = (
            _enum(OrderStatus, d.get("order_status", ""), "order_status", errors, line)
            if d.get("order_status")
            else None
        )
        rating = None
        if d.get("customer_rating"):
            if d["customer_rating"].isdigit() and 1 <= int(d["customer_rating"]) <= 5:
                rating = int(d["customer_rating"])
            else:
                errors.append({"line": line, "field": "customer_rating", "message": "must be 1 to 5"})
        if order_date and delivery and delivery < order_date:
            errors.append({"line": line, "field": "delivery_date", "message": "is before order_date"})
        if order_status == OrderStatus.DELIVERED and not delivery:
            errors.append({"line": line, "field": "delivery_date", "message": "required when DELIVERED"})

        ret = None
        if d.get("return_id"):
            if d["return_id"] in existing_returns:
                errors.append({"line": line, "field": "return_id", "message": "duplicate return_id"})
            if order_status and order_status != OrderStatus.DELIVERED:
                errors.append(
                    {"line": line, "field": "return_id", "message": "only DELIVERED orders can be returned"}
                )
            rdate = _parse_date(d.get("return_date", ""), "return_date", errors, line)
            if rdate and delivery and rdate < delivery:
                errors.append({"line": line, "field": "return_date", "message": "is before delivery_date"})
            code = _enum(ReasonCode, d.get("reason_code", ""), "reason_code", errors, line)
            rstatus = _enum(
                ReturnStatus, d.get("return_status", "") or "REQUESTED", "return_status", errors, line
            )
            refund = _parse_money(d.get("refund_amount", "") or "0", "refund_amount", errors, line)
            if refund is not None and amount is not None and refund > amount:
                errors.append({"line": line, "field": "refund_amount", "message": "exceeds order_amount"})
            mismatch = d.get("mismatch_flag", "").lower() in ("1", "true", "yes", "y")
            ret = (d["return_id"], code, d.get("reason_text") or None, rdate, mismatch, refund, rstatus)
        parsed.append((d, order_date, delivery, amount, order_status, rating, ret))

    if errors:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": f"{len(errors)} problem(s) found; nothing was imported",
                "errors": errors[:200],
            },
        )

    created = {"customers": 0, "products": 0, "orders": 0, "returns": 0}
    for d, order_date, delivery, amount, order_status, rating, ret in parsed:
        customer = customers.get(d["customer_id"])
        if customer is None:
            customer = Customer(
                customer_id=d["customer_id"], name=d["customer_name"], email=d["customer_email"]
            )
            db.add(customer)
            customers[customer.customer_id] = customer
            created["customers"] += 1
        product = products.get(d["product_id"])
        if product is None:
            product = Product(
                product_id=d["product_id"],
                product_name=d["product_name"],
                category=d["category"],
                category_risk=0,
            )
            db.add(product)
            products[product.product_id] = product
            created["products"] += 1
        db.flush()
        order = Order(
            order_id=d["order_id"],
            customer_id=customer.id,
            product_id=product.id,
            order_date=order_date,
            delivery_date=delivery,
            order_amount=amount,
            order_status=order_status,
            customer_rating=rating,
        )
        db.add(order)
        db.flush()
        created["orders"] += 1
        if ret:
            rid, code, text, rdate, mismatch, refund, rstatus = ret
            db.add(
                Return(
                    return_id=rid,
                    order_id=order.id,
                    customer_id=customer.id,
                    reason_code=code,
                    reason_text=text,
                    return_date=rdate,
                    days_to_return=(rdate - delivery).days,
                    mismatch_flag=mismatch,
                    refund_amount=refund,
                    return_status=rstatus,
                )
            )
            created["returns"] += 1
    db.flush()
    recompute_category_risk(db)
    rescored = assess_all(db)
    return {"imported": created, "rescored": rescored}


def export_flagged_csv(db: Session, risk_level: RiskLevel | None, min_score: int | None) -> str:
    stmt, cols = customer_overview()
    stmt = stmt.where(RiskAssessment.id.is_not(None))
    if risk_level:
        stmt = stmt.where(RiskAssessment.risk_level == risk_level)
    if min_score is not None:
        stmt = stmt.where(RiskAssessment.risk_score >= min_score)
    rows = db.execute(stmt.order_by(RiskAssessment.risk_score.desc(), Customer.customer_id))
    buf = io.StringIO()
    w = csv.writer(buf)
    # No email or other contact details in exports.
    w.writerow(
        [
            "customer_id",
            "name",
            "risk_score",
            "risk_level",
            "total_orders",
            "total_returns",
            "return_percentage",
            "last_return_date",
            "review_status",
            "top_risk_factors",
            "assessed_at",
        ]
    )
    for r in rows:
        a = r.RiskAssessment
        factors = "; ".join(f"{f['factor']} (+{f['contribution']})" for f in a.risk_factors[:3])
        w.writerow(
            [
                r.Customer.customer_id,
                r.Customer.name,
                a.risk_score,
                a.risk_level.value,
                r.orders,
                r.returns,
                round(float(r.ratio) * 100, 1),
                r.last_return_date or "",
                r.review_status.value if r.review_status else "",
                factors,
                a.assessed_at.isoformat(),
            ]
        )
    return buf.getvalue()
