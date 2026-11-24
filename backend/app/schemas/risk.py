from datetime import datetime

from pydantic import BaseModel

from app.models import ReviewStatus, RiskLevel, ScoringMethod


class RiskFactorOut(BaseModel):
    rule_id: str
    factor: str
    group: str
    contribution: int
    raw_points: int
    description: str


class AssessmentOut(BaseModel):
    customer_id: str
    risk_score: int
    risk_level: RiskLevel
    risk_factors: list[RiskFactorOut]
    requires_manual_review: bool
    scoring_method: ScoringMethod
    config_version: str
    notes: list[str]
    features: dict
    assessed_at: datetime


class AssessmentHistoryItem(BaseModel):
    risk_score: int
    risk_level: RiskLevel
    config_version: str
    assessed_at: datetime


class AssessAllResult(BaseModel):
    assessed: int
    LOW: int
    MEDIUM: int
    HIGH: int
    duration_ms: int


class HighRiskItem(BaseModel):
    customer_id: str
    name: str
    risk_score: int
    risk_level: RiskLevel
    top_factors: list[RiskFactorOut]
    review_status: ReviewStatus | None
    review_updated_at: datetime | None
    assessed_at: datetime


class LevelCount(BaseModel):
    risk_level: RiskLevel
    count: int
    percentage: float


class RiskSummary(BaseModel):
    total_assessed: int
    levels: list[LevelCount]
    average_score: float
    requires_review: int
