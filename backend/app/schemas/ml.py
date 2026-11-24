from pydantic import BaseModel, Field, model_validator


class FeatureInput(BaseModel):
    total_orders: int = Field(ge=0)
    total_returns: int = Field(ge=0)
    returns_last_90d: int = Field(default=0, ge=0)
    vague_reason_count: int = Field(default=0, ge=0)
    top_reason_share: float | None = Field(default=None, ge=0, le=1)
    avg_return_window: float | None = Field(default=None, ge=0)
    high_risk_category_share: float | None = Field(default=None, ge=0, le=1)
    mismatch_count: int = Field(default=0, ge=0)
    returned_high_rating_count: int = Field(default=0, ge=0)
    return_rate_trend: float | None = Field(default=None, ge=0)


class PredictRequest(BaseModel):
    customer_id: str | None = None
    features: FeatureInput | None = None
    model: str = Field(default="selected", pattern="^(selected|logistic_regression|decision_tree)$")

    @model_validator(mode="after")
    def _one_source(self) -> "PredictRequest":
        if (self.customer_id is None) == (self.features is None):
            raise ValueError("Provide exactly one of customer_id or features")
        return self


class PredictResponse(BaseModel):
    customer_id: str | None
    model: str
    probability_suspicious_pattern: float
    predicted_label: str
    threshold: float
    rule_based_score: int | None
    rule_based_level: str | None
    disclaimer: str
