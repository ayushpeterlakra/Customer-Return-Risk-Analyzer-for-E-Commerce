"""Feature extraction: turns one customer's orders and returns into numbers.

Inputs are plain records so the same code serves the API, the unit tests and
the ML training script.
"""

from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date


@dataclass(frozen=True)
class OrderRecord:
    order_date: date
    status: str  # PLACED | SHIPPED | DELIVERED | CANCELLED
    category: str | None = None
    rating: int | None = None


@dataclass(frozen=True)
class ReturnRecord:
    return_date: date
    days_to_return: int | None
    reason_code: str | None
    reason_text: str | None = None
    mismatch: bool = False
    status: str = "APPROVED"  # REJECTED returns are ignored
    category: str | None = None
    rating: int | None = None  # rating the customer gave the returned order


@dataclass
class CustomerFeatures:
    total_orders: int = 0
    total_returns: int = 0
    return_ratio: float | None = None
    returns_last_90d: int = 0
    returns_prior_window: int = 0
    return_rate_trend: float | None = None
    vague_reason_count: int = 0
    top_reason: str | None = None
    top_reason_share: float | None = None
    avg_return_window: float | None = None
    high_risk_category_share: float | None = None
    mismatch_count: int = 0
    returned_high_rating_count: int = 0
    data_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        for key in (
            "return_ratio",
            "return_rate_trend",
            "top_reason_share",
            "avg_return_window",
            "high_risk_category_share",
        ):
            if data[key] is not None:
                data[key] = round(data[key], 4)
        return data


def is_vague(reason_code: str | None, reason_text: str | None, vague_codes: set[str], min_len: int) -> bool:
    if reason_code is None:
        return True
    if reason_code not in vague_codes:
        return False
    return len((reason_text or "").strip()) < min_len


def compute_features(
    orders: list[OrderRecord],
    returns: list[ReturnRecord],
    *,
    as_of: date,
    vague_codes: set[str],
    vague_text_min_length: int,
    high_risk_categories: set[str],
    high_rating: int = 4,
) -> CustomerFeatures:
    f = CustomerFeatures()
    active_orders = [o for o in orders if o.status != "CANCELLED"]
    counted = [r for r in returns if r.status != "REJECTED"]

    f.total_orders = len(active_orders)
    f.total_returns = len(counted)

    if f.total_orders > 0:
        f.return_ratio = f.total_returns / f.total_orders
        if f.total_returns > f.total_orders:
            f.data_issues.append("More returns than orders; ratio capped at 1.0")
            f.return_ratio = 1.0

    if not counted:
        return f

    # Time-based behaviour: recent 90 days versus the 90-365 day window, as monthly rates.
    ages = [(as_of - r.return_date).days for r in counted]
    if any(age < 0 for age in ages):
        f.data_issues.append("Return dated in the future; ignored for trend")
    f.returns_last_90d = sum(1 for a in ages if 0 <= a <= 90)
    f.returns_prior_window = sum(1 for a in ages if 90 < a <= 365)
    if f.returns_prior_window > 0:
        f.return_rate_trend = (f.returns_last_90d / 3) / (f.returns_prior_window / 9)

    f.vague_reason_count = sum(
        1 for r in counted if is_vague(r.reason_code, r.reason_text, vague_codes, vague_text_min_length)
    )
    reasons = Counter(r.reason_code or "UNKNOWN" for r in counted)
    f.top_reason, top_count = reasons.most_common(1)[0]
    f.top_reason_share = top_count / f.total_returns

    windows = [r.days_to_return for r in counted if r.days_to_return is not None]
    negative = [w for w in windows if w < 0]
    if negative:
        f.data_issues.append(f"{len(negative)} return(s) dated before delivery; excluded from timing")
    windows = [w for w in windows if w >= 0]
    if windows:
        f.avg_return_window = sum(windows) / len(windows)
    if len(windows) < len(counted) and not negative:
        f.data_issues.append("Some returns have no delivery date; excluded from timing")

    with_category = [r for r in counted if r.category]
    if with_category:
        f.high_risk_category_share = sum(
            1 for r in with_category if r.category in high_risk_categories
        ) / len(with_category)

    f.mismatch_count = sum(1 for r in counted if r.mismatch)
    f.returned_high_rating_count = sum(1 for r in counted if r.rating is not None and r.rating >= high_rating)
    return f
