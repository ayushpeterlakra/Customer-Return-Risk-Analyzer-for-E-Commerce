from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models import ReviewStatus, RiskLevel


class ReviewUpdate(BaseModel):
    review_status: ReviewStatus
    review_notes: str | None = Field(default=None, max_length=2000)
    updated_by: str = Field(min_length=1, max_length=120)

    @field_validator("updated_by")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("updated_by must not be blank")
        return v


class ReviewRecordOut(BaseModel):
    id: int
    customer_id: str
    previous_status: ReviewStatus | None
    review_status: ReviewStatus
    review_notes: str | None
    updated_by: str
    updated_at: datetime


class ReviewListItem(BaseModel):
    customer_id: str
    name: str
    review_status: ReviewStatus
    updated_by: str
    updated_at: datetime
    risk_score: int | None
    risk_level: RiskLevel | None
