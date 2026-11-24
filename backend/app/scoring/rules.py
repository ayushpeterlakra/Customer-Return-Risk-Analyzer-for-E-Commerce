"""One function per rule. Each returns a RuleHit when it fires, else None.

A rule only reads CustomerFeatures and its own config section, so adding or
changing a rule never touches the API or database code.
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.scoring.config import ScoringConfig
from app.scoring.features import CustomerFeatures


@dataclass(frozen=True)
class RuleHit:
    rule_id: str
    group: str
    factor: str
    points: int
    description: str


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def very_high_return_ratio(f: CustomerFeatures, c: ScoringConfig) -> RuleHit | None:
    r = c.rules.very_high_return_ratio
    if (
        r.enabled
        and f.return_ratio is not None
        and f.total_orders >= r.min_orders
        and f.return_ratio > r.threshold
    ):
        return RuleHit(
            "very_high_return_ratio",
            "return_volume",
            "Very high return ratio",
            r.points,
            f"Returned {f.total_returns} of {f.total_orders} orders ({_pct(f.return_ratio)}), "
            f"above the {_pct(r.threshold)} threshold.",
        )
    return None


def high_return_ratio(f: CustomerFeatures, c: ScoringConfig) -> RuleHit | None:
    r = c.rules.high_return_ratio
    if (
        r.enabled
        and f.return_ratio is not None
        and f.total_orders >= r.min_orders
        and f.return_ratio > r.threshold
    ):
        return RuleHit(
            "high_return_ratio",
            "return_volume",
            "High return ratio",
            r.points,
            f"Returned {f.total_returns} of {f.total_orders} orders ({_pct(f.return_ratio)}), "
            f"above the {_pct(r.threshold)} threshold.",
        )
    return None


def high_return_frequency(f: CustomerFeatures, c: ScoringConfig) -> RuleHit | None:
    r = c.rules.high_return_frequency
    if r.enabled and f.returns_last_90d >= r.min_returns_90d:
        return RuleHit(
            "high_return_frequency",
            "return_volume",
            "High return frequency",
            r.points,
            f"{f.returns_last_90d} returns in the last 90 days (limit {r.min_returns_90d - 1}).",
        )
    return None


def vague_reasons(f: CustomerFeatures, c: ScoringConfig) -> RuleHit | None:
    r = c.rules.vague_reasons
    if r.enabled and f.vague_reason_count >= r.min_count:
        return RuleHit(
            "vague_reasons",
            "return_reasons",
            "Vague return reasons",
            r.points,
            f"{f.vague_reason_count} returns gave a vague reason with no explanation "
            f"(limit {r.min_count - 1}).",
        )
    return None


def repeated_reason(f: CustomerFeatures, c: ScoringConfig) -> RuleHit | None:
    r = c.rules.repeated_reason
    if (
        r.enabled
        and f.top_reason_share is not None
        and f.total_returns >= r.min_returns
        and f.top_reason_share >= r.min_share
    ):
        label = (f.top_reason or "UNKNOWN").replace("_", " ").lower()
        return RuleHit(
            "repeated_reason",
            "return_reasons",
            "Repeated identical reason",
            r.points,
            f'{_pct(f.top_reason_share)} of {f.total_returns} returns used the same reason ("{label}").',
        )
    return None


def mismatch_history(f: CustomerFeatures, c: ScoringConfig) -> RuleHit | None:
    r = c.rules.mismatch_history
    if not r.enabled or f.mismatch_count == 0:
        return None
    multi = f.mismatch_count >= r.multi_threshold
    return RuleHit(
        "mismatch_history",
        "item_mismatch",
        "Item mismatch history",
        r.multi_points if multi else r.points,
        f"{f.mismatch_count} return(s) where the item sent back did not match the item ordered.",
    )


def short_return_window(f: CustomerFeatures, c: ScoringConfig) -> RuleHit | None:
    r = c.rules.short_return_window
    if (
        r.enabled
        and f.avg_return_window is not None
        and f.total_returns >= r.min_returns
        and f.avg_return_window < r.max_avg_days
    ):
        return RuleHit(
            "short_return_window",
            "return_timing",
            "Short return window",
            r.points,
            f"Average {f.avg_return_window:.1f} days from delivery to return, "
            f"under the {r.max_avg_days:g}-day threshold.",
        )
    return None


def high_return_categories(f: CustomerFeatures, c: ScoringConfig) -> RuleHit | None:
    r = c.rules.high_return_categories
    if (
        r.enabled
        and f.high_risk_category_share is not None
        and f.total_returns >= r.min_returns
        and f.high_risk_category_share >= r.min_share
    ):
        return RuleHit(
            "high_return_categories",
            "behaviour",
            "Returns concentrated in high-return categories",
            r.points,
            f"{_pct(f.high_risk_category_share)} of returns are in categories with above-average "
            f"return rates. This alone is not suspicious; it adds weight to other signals.",
        )
    return None


def returns_after_high_rating(f: CustomerFeatures, c: ScoringConfig) -> RuleHit | None:
    r = c.rules.returns_after_high_rating
    if r.enabled and f.returned_high_rating_count >= r.min_count:
        return RuleHit(
            "returns_after_high_rating",
            "behaviour",
            "Returned items rated highly",
            r.points,
            f"{f.returned_high_rating_count} returned items were rated {r.min_rating} stars or more, "
            f"which can indicate use-and-return behaviour.",
        )
    return None


def rising_return_rate(f: CustomerFeatures, c: ScoringConfig) -> RuleHit | None:
    r = c.rules.rising_return_rate
    if (
        r.enabled
        and f.return_rate_trend is not None
        and f.returns_last_90d >= r.min_recent_returns
        and f.return_rate_trend >= r.min_trend
    ):
        return RuleHit(
            "rising_return_rate",
            "behaviour",
            "Rising return rate",
            r.points,
            f"Monthly return rate in the last 90 days is {f.return_rate_trend:.1f}x the rate "
            f"of the previous 9 months.",
        )
    return None


Rule = Callable[[CustomerFeatures, ScoringConfig], RuleHit | None]

# Order matters only for display; very_high_return_ratio supersedes high_return_ratio in the engine.
ALL_RULES: list[Rule] = [
    very_high_return_ratio,
    high_return_ratio,
    high_return_frequency,
    vague_reasons,
    repeated_reason,
    mismatch_history,
    short_return_window,
    high_return_categories,
    returns_after_high_rating,
    rising_return_rate,
]
