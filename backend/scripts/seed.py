"""Populate PostgreSQL with reproducible SYNTHETIC demo data, then score every customer.

Usage (from backend/):
    python -m scripts.seed                  # seed 42, 300 customers, dates relative to today
    python -m scripts.seed --as-of 2026-11-24 --customers 400 --seed 7

The hidden behaviour profile of each synthetic customer is written to
data/synthetic_labels.csv (used only to train and evaluate the ML demo). It is
not stored in the application database and is never shown as a fraud label.
"""

import argparse
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import text

from app.db import session_factory
from app.models import (
    Customer,
    Order,
    OrderStatus,
    Product,
    ReasonCode,
    Return,
    ReturnStatus,
)
from app.services.scoring_service import assess_all, recompute_category_risk
from scripts.generate_data import generate

LABELS_PATH = Path(__file__).resolve().parents[1] / "data" / "synthetic_labels.csv"


def seed(
    seed_value: int = 42, n_customers: int = 300, as_of: date | None = None, labels_path: Path = LABELS_PATH
) -> dict:
    ds = generate(seed_value, n_customers, as_of)
    Session = session_factory()
    with Session.begin() as db:
        db.execute(
            text(
                "TRUNCATE review_records, risk_assessments, returns, orders, products, customers "
                "RESTART IDENTITY CASCADE"
            )
        )
        products = [
            Product(
                product_id=p.product_id,
                product_name=p.product_name,
                category=p.category,
                category_risk=p.category_risk,
            )
            for p in ds.products
        ]
        customers = [
            Customer(customer_id=c.customer_id, name=c.name, email=c.email, created_at=c.created_at)
            for c in ds.customers
        ]
        db.add_all(products + customers)
        db.flush()
        orders = [
            Order(
                order_id=o.order_id,
                customer_id=customers[o.customer_idx].id,
                product_id=products[o.product_idx].id,
                order_date=o.order_date,
                delivery_date=o.delivery_date,
                order_amount=o.order_amount,
                order_status=OrderStatus(o.order_status),
                customer_rating=o.customer_rating,
            )
            for o in ds.orders
        ]
        db.add_all(orders)
        db.flush()
        db.add_all(
            [
                Return(
                    return_id=r.return_id,
                    order_id=orders[r.order_idx].id,
                    customer_id=customers[r.customer_idx].id,
                    reason_code=ReasonCode(r.reason_code),
                    reason_text=r.reason_text,
                    return_date=r.return_date,
                    days_to_return=r.days_to_return,
                    mismatch_flag=r.mismatch_flag,
                    refund_amount=r.refund_amount,
                    return_status=ReturnStatus(r.return_status),
                )
                for r in ds.returns
            ]
        )
        db.flush()
        recompute_category_risk(db)
        summary = assess_all(db)

    labels_path.parent.mkdir(parents=True, exist_ok=True)
    with labels_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["customer_id", "synthetic_profile", "synthetic_suspicious_label"])
        for c in ds.customers:
            writer.writerow([c.customer_id, c.profile, int(c.suspicious)])

    return {
        "customers": len(ds.customers),
        "products": len(ds.products),
        "orders": len(ds.orders),
        "returns": len(ds.returns),
        **{f"risk_{k.lower()}": v for k, v in summary.items() if k != "assessed"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed SYNTHETIC demo data")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--customers", type=int, default=300)
    parser.add_argument(
        "--as-of", type=date.fromisoformat, default=None, help="Reference date, default today"
    )
    args = parser.parse_args()
    result = seed(args.seed, args.customers, args.as_of)
    print("Seeded SYNTHETIC demonstration data:")
    for key, value in result.items():
        print(f"  {key:>12}: {value}")
    print(f"  labels file : {LABELS_PATH}")


if __name__ == "__main__":
    main()
