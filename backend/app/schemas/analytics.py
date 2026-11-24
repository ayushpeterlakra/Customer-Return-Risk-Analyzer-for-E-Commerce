from datetime import date

from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    total_customers: int
    total_orders: int
    total_returns: int
    average_return_ratio: float
    high_risk_customers: int
    medium_risk_customers: int
    low_risk_customers: int
    total_refunded: float
    date_from: date | None
    date_to: date | None


class CategoryReturns(BaseModel):
    category: str
    orders: int
    returns: int
    return_rate: float
    mismatches: int


class TrendPoint(BaseModel):
    period_start: date
    returns: int
    orders: int
    mismatches: int


class RatioBucket(BaseModel):
    bucket: str
    lower: float
    upper: float
    customers: int


class ReasonCount(BaseModel):
    reason_code: str
    count: int
    vague: int
