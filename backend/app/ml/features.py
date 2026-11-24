"""Feature columns shared by training and prediction (single source of truth)."""

FEATURE_COLUMNS = [
    "total_orders",
    "total_returns",
    "return_ratio",
    "returns_last_90d",
    "return_rate_trend",
    "vague_reason_count",
    "vague_reason_share",
    "top_reason_share",
    "avg_return_window",
    "high_risk_category_share",
    "mismatch_count",
    "returned_high_rating_count",
]


def to_row(f: dict) -> dict:
    """Map a CustomerFeatures dict to model inputs. Missing values stay None; the pipeline imputes them."""
    returns = f.get("total_returns") or 0
    orders = f.get("total_orders") or 0
    return {
        "total_orders": orders,
        "total_returns": returns,
        "return_ratio": (returns / orders) if orders else None,
        "returns_last_90d": f.get("returns_last_90d", 0),
        "return_rate_trend": f.get("return_rate_trend"),
        "vague_reason_count": f.get("vague_reason_count", 0),
        "vague_reason_share": (f.get("vague_reason_count", 0) / returns) if returns else 0.0,
        "top_reason_share": f.get("top_reason_share"),
        "avg_return_window": f.get("avg_return_window"),
        "high_risk_category_share": f.get("high_risk_category_share"),
        "mismatch_count": f.get("mismatch_count", 0),
        "returned_high_rating_count": f.get("returned_high_rating_count", 0),
    }
