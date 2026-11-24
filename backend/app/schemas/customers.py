from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models import OrderStatus, ReasonCode, ReturnStatus, ReviewStatus, RiskLevel
from app.schemas.risk import AssessmentOut


class CustomerListItem(BaseModel):
    customer_id: str
    name: str
    total_orders: int
    total_returns: int
    return_percentage: float
    risk_score: int | None
    risk_level: RiskLevel | None
    last_return_date: date | None
    review_status: ReviewStatus | None


class CategoryCount(BaseModel):
    category: str
    orders: int
    returns: int


class CustomerDetail(BaseModel):
    customer_id: str
    name: str
    email: str
    created_at: datetime
    total_orders: int
    total_returns: int
    return_percentage: float
    total_order_value: Decimal
    total_refunded: Decimal
    mismatch_count: int
    last_return_date: date | None
    review_status: ReviewStatus | None
    latest_assessment: AssessmentOut | None
    categories: list[CategoryCount]


class OrderOut(BaseModel):
    order_id: str
    product_id: str
    product_name: str
    category: str
    order_date: date
    delivery_date: date | None
    order_amount: Decimal
    order_status: OrderStatus
    customer_rating: int | None
    returned: bool


class ReturnOut(BaseModel):
    return_id: str
    order_id: str
    product_name: str
    category: str
    order_date: date
    delivery_date: date | None
    return_date: date
    days_to_return: int
    reason_code: ReasonCode
    reason_text: str | None
    is_vague: bool
    mismatch_flag: bool
    refund_amount: Decimal
    return_status: ReturnStatus
