"""Rule-based return risk scoring.

This package is pure Python: it imports nothing from the web or database layers,
so rules can be changed and unit-tested in isolation.
"""

from app.scoring.config import ScoringConfig, load_default_config
from app.scoring.engine import RiskFactor, RiskResult, score_customer
from app.scoring.features import CustomerFeatures, OrderRecord, ReturnRecord, compute_features

__all__ = [
    "CustomerFeatures",
    "OrderRecord",
    "ReturnRecord",
    "RiskFactor",
    "RiskResult",
    "ScoringConfig",
    "compute_features",
    "load_default_config",
    "score_customer",
]
