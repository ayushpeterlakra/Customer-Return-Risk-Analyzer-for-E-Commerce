"""Combines rule hits into a 0-100 score with group caps and an explanation."""

from collections import defaultdict
from dataclasses import asdict, dataclass, field

from app.scoring.config import ScoringConfig
from app.scoring.features import CustomerFeatures
from app.scoring.rules import ALL_RULES, Rule, RuleHit


@dataclass
class RiskFactor:
    rule_id: str
    factor: str
    group: str
    raw_points: int
    contribution: int
    description: str


@dataclass
class RiskResult:
    risk_score: int
    risk_level: str
    requires_manual_review: bool
    risk_factors: list[RiskFactor]
    notes: list[str] = field(default_factory=list)
    config_version: str = ""

    def factors_as_dicts(self) -> list[dict]:
        return [asdict(f) for f in self.risk_factors]


def classify(score: int, config: ScoringConfig) -> str:
    if score <= config.levels.low_max:
        return "LOW"
    if score <= config.levels.medium_max:
        return "MEDIUM"
    return "HIGH"


def score_customer(
    features: CustomerFeatures, config: ScoringConfig, rules: list[Rule] | None = None
) -> RiskResult:
    notes = list(features.data_issues)
    if features.total_orders == 0:
        notes.append("No completed orders on record; not enough history to score.")
        return RiskResult(0, "LOW", False, [], notes, config.version)

    hits: list[RuleHit] = [h for rule in (rules or ALL_RULES) if (h := rule(features, config)) is not None]
    # The stronger ratio rule replaces the weaker one instead of stacking.
    if any(h.rule_id == "very_high_return_ratio" for h in hits):
        hits = [h for h in hits if h.rule_id != "high_return_ratio"]

    caps = config.group_caps.model_dump()
    by_group: dict[str, list[RuleHit]] = defaultdict(list)
    for hit in hits:
        by_group[hit.group].append(hit)

    factors: list[RiskFactor] = []
    for group, group_hits in by_group.items():
        remaining = caps.get(group, 100)
        # Largest signals first, so the cap trims the weakest ones.
        for hit in sorted(group_hits, key=lambda h: -h.points):
            counted = min(hit.points, remaining)
            remaining -= counted
            description = hit.description
            if counted < hit.points:
                description += (
                    f" (Counted {counted} of {hit.points} points: {group.replace('_', ' ')} cap reached.)"
                )
            factors.append(RiskFactor(hit.rule_id, hit.factor, group, hit.points, counted, description))

    factors = [f for f in factors if f.contribution > 0] + [f for f in factors if f.contribution == 0]
    factors.sort(key=lambda f: -f.contribution)
    total = sum(f.contribution for f in factors)
    score = max(0, min(100, total))
    if total > 100:
        notes.append(f"Factors add up to {total} points; the score is capped at 100.")
    if features.total_returns == 0:
        notes.append("No returns on record.")
    level = classify(score, config)
    return RiskResult(score, level, level == "HIGH", factors, notes, config.version)
