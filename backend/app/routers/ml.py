from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_tx
from app.ml import predictor
from app.schemas.ml import PredictRequest, PredictResponse
from app.services.customers_service import get_customer
from app.services.scoring_service import features_for_customers

router = APIRouter(prefix="/api/ml", tags=["ml"])
DB = Annotated[Session, Depends(get_tx)]

DISCLAIMER = (
    "Model trained on synthetic demonstration data. The probability estimates how closely this "
    "behaviour resembles the synthetic suspicious patterns; it is not evidence of fraud."
)


@router.post(
    "/predict", response_model=PredictResponse, summary="ML probability of a suspicious return pattern"
)
def predict(body: PredictRequest, db: DB):
    score = level = None
    if body.customer_id:
        customer = get_customer(db, body.customer_id)
        features = features_for_customers(db, [customer])[customer.id]
        if customer.latest_assessment:
            score, level = customer.latest_assessment.risk_score, customer.latest_assessment.risk_level.value
    else:
        features = body.features.model_dump()
    try:
        name, probability, threshold = predictor.predict(features, body.model)
    except predictor.ModelUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    return PredictResponse(
        customer_id=body.customer_id,
        model=name,
        probability_suspicious_pattern=round(probability, 4),
        predicted_label="resembles suspicious pattern"
        if probability >= threshold
        else "resembles normal pattern",
        threshold=round(threshold, 4),
        rule_based_score=score,
        rule_based_level=level,
        disclaimer=DISCLAIMER,
    )


@router.get("/metrics", summary="Stored evaluation metrics from the last training run")
def metrics():
    try:
        return predictor.load_metrics()
    except predictor.ModelUnavailable as exc:
        raise HTTPException(404, str(exc)) from exc
