from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    OrderStatus,
    ReasonCode,
    ReturnStatus,
    ReviewStatus,
    RiskLevel,
    ScoringMethod,
)


def _enum(e: type, name: str) -> Enum:
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    latest_assessment_id: Mapped[int | None] = mapped_column(
        ForeignKey("risk_assessments.id", ondelete="SET NULL", use_alter=True), nullable=True
    )

    orders: Mapped[list["Order"]] = relationship(back_populates="customer")
    returns: Mapped[list["Return"]] = relationship(back_populates="customer", overlaps="returns")
    latest_assessment: Mapped["RiskAssessment | None"] = relationship(
        foreign_keys=[latest_assessment_id], post_update=True
    )


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("category_risk >= 0 AND category_risk <= 1", name="category_risk_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    product_name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(60), index=True)
    category_risk: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("0"))

    orders: Mapped[list["Order"]] = relationship(back_populates="product")


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("id", "customer_id", name="uq_orders_id_customer"),
        CheckConstraint("order_amount >= 0", name="order_amount_non_negative"),
        CheckConstraint("delivery_date IS NULL OR delivery_date >= order_date", name="delivery_after_order"),
        CheckConstraint("customer_rating IS NULL OR (customer_rating BETWEEN 1 AND 5)", name="rating_range"),
        CheckConstraint(
            "order_status <> 'DELIVERED' OR delivery_date IS NOT NULL", name="delivered_has_date"
        ),
        Index("ix_orders_order_date", "order_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    order_date: Mapped[date] = mapped_column(Date)
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    order_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    order_status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus, "order_status"))
    customer_rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    customer: Mapped[Customer] = relationship(back_populates="orders")
    product: Mapped[Product] = relationship(back_populates="orders")
    return_: Mapped["Return | None"] = relationship(back_populates="order", uselist=False, overlaps="returns")


class Return(TimestampMixin, Base):
    __tablename__ = "returns"
    __table_args__ = (
        # The return's customer must be the order's customer.
        ForeignKeyConstraint(
            ["order_id", "customer_id"],
            ["orders.id", "orders.customer_id"],
            name="fk_returns_order_customer",
            ondelete="RESTRICT",
        ),
        CheckConstraint("days_to_return >= 0", name="days_to_return_non_negative"),
        CheckConstraint("refund_amount >= 0", name="refund_non_negative"),
        Index("ix_returns_return_date", "return_date"),
        Index("ix_returns_reason_code", "reason_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    return_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    order_id: Mapped[int] = mapped_column(Integer, unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True)
    reason_code: Mapped[ReasonCode] = mapped_column(_enum(ReasonCode, "reason_code"))
    reason_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    return_date: Mapped[date] = mapped_column(Date)
    days_to_return: Mapped[int] = mapped_column(Integer)
    mismatch_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    return_status: Mapped[ReturnStatus] = mapped_column(_enum(ReturnStatus, "return_status"))

    order: Mapped[Order] = relationship(back_populates="return_", foreign_keys=[order_id], overlaps="returns")
    customer: Mapped[Customer] = relationship(back_populates="returns", overlaps="return_,order")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        CheckConstraint("risk_score BETWEEN 0 AND 100", name="risk_score_range"),
        Index("ix_risk_assessments_customer_assessed", "customer_id", "assessed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"))
    risk_score: Mapped[int] = mapped_column(SmallInteger, index=True)
    risk_level: Mapped[RiskLevel] = mapped_column(_enum(RiskLevel, "risk_level"), index=True)
    scoring_method: Mapped[ScoringMethod] = mapped_column(_enum(ScoringMethod, "scoring_method"))
    config_version: Mapped[str] = mapped_column(String(40))
    risk_factors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, default=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewRecord(Base):
    """Append-only: each row is one review status change (the audit trail)."""

    __tablename__ = "review_records"
    __table_args__ = (Index("ix_review_records_customer_updated", "customer_id", "updated_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"))
    previous_status: Mapped[ReviewStatus | None] = mapped_column(
        _enum(ReviewStatus, "review_status"), nullable=True
    )
    review_status: Mapped[ReviewStatus] = mapped_column(_enum(ReviewStatus, "review_status"))
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[str] = mapped_column(String(120))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScoringConfigRecord(Base):
    """Versioned scoring rules edited from the Settings page. The newest row is active."""

    __tablename__ = "scoring_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(40), unique=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    updated_by: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
