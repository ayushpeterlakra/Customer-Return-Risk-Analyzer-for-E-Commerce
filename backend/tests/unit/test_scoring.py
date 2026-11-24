from datetime import date, timedelta

import pytest

from app.scoring import (
    CustomerFeatures,
    OrderRecord,
    ReturnRecord,
    compute_features,
    load_default_config,
    score_customer,
)
from app.scoring.engine import classify
from app.scoring.rules import (
    high_return_categories,
    high_return_frequency,
    high_return_ratio,
    mismatch_history,
    repeated_reason,
    returns_after_high_rating,
    rising_return_rate,
    short_return_window,
    vague_reasons,
    very_high_return_ratio,
)

CFG = load_default_config()
AS_OF = date(2026, 11, 15)
VAGUE = set(CFG.vague_reason_codes)


def feats(**kw) -> CustomerFeatures:
    return CustomerFeatures(**kw)


def build(orders: int, returns: list[ReturnRecord], cancelled: int = 0):
    order_list = [OrderRecord(AS_OF - timedelta(days=200), "DELIVERED", "Books") for _ in range(orders)]
    order_list += [OrderRecord(AS_OF, "CANCELLED") for _ in range(cancelled)]
    return compute_features(
        order_list,
        returns,
        as_of=AS_OF,
        vague_codes=VAGUE,
        vague_text_min_length=CFG.vague_text_min_length,
        high_risk_categories={"Fashion", "Shoes"},
    )


def ret(
    days_ago=30,
    window=5,
    code="SIZE_FIT",
    text="Too small in the shoulders",
    mismatch=False,
    category="Books",
    rating=None,
    status="APPROVED",
):
    return ReturnRecord(
        AS_OF - timedelta(days=days_ago), window, code, text, mismatch, status, category, rating
    )


# ---- Feature extraction -------------------------------------------------------------


def test_features_ignore_cancelled_orders_and_rejected_returns():
    f = build(4, [ret(), ret(status="REJECTED")], cancelled=3)
    assert f.total_orders == 4
    assert f.total_returns == 1
    assert f.return_ratio == pytest.approx(0.25)


def test_vague_reason_needs_vague_code_and_no_explanation():
    f = build(
        5,
        [
            ret(code="DEFECTIVE", text=None),
            ret(code="DEFECTIVE", text="Screen flickers after two days"),
            ret(code="SIZE_FIT", text=None),
        ],
    )
    assert f.vague_reason_count == 1


def test_trend_compares_recent_monthly_rate_with_prior_window():
    f = build(10, [ret(days_ago=10), ret(days_ago=20), ret(days_ago=30), ret(days_ago=200)])
    assert f.returns_last_90d == 3
    assert f.returns_prior_window == 1
    assert f.return_rate_trend == pytest.approx((3 / 3) / (1 / 9))


def test_inconsistent_data_is_reported_not_hidden():
    f = build(1, [ret(), ret(), ret(window=-2)])
    assert f.return_ratio == 1.0
    assert any("More returns than orders" in i for i in f.data_issues)
    assert any("before delivery" in i for i in f.data_issues)
    assert f.avg_return_window == 5


def test_missing_delivery_dates_are_excluded_from_timing():
    f = build(5, [ret(window=None), ret(window=4)])
    assert f.avg_return_window == 4
    assert any("no delivery date" in i for i in f.data_issues)


# ---- Each rule ----------------------------------------------------------------------


@pytest.mark.parametrize("ratio,orders,fires", [(0.41, 3, True), (0.40, 3, False), (0.9, 2, False)])
def test_high_return_ratio(ratio, orders, fires):
    hit = high_return_ratio(feats(total_orders=orders, total_returns=1, return_ratio=ratio), CFG)
    assert (hit is not None) == fires
    if hit:
        assert hit.points == 30


def test_very_high_return_ratio_needs_five_orders():
    assert very_high_return_ratio(feats(total_orders=4, return_ratio=0.8), CFG) is None
    assert very_high_return_ratio(feats(total_orders=5, return_ratio=0.8), CFG).points == 35


def test_high_return_frequency():
    assert high_return_frequency(feats(returns_last_90d=3), CFG) is None
    assert high_return_frequency(feats(returns_last_90d=4), CFG).points == 15


def test_vague_reasons_fires_above_two():
    assert vague_reasons(feats(vague_reason_count=2), CFG) is None
    assert vague_reasons(feats(vague_reason_count=3), CFG).points == 15


def test_repeated_reason_requires_enough_returns():
    assert repeated_reason(feats(total_returns=3, top_reason_share=1.0, top_reason="OTHER"), CFG) is None
    assert (
        repeated_reason(feats(total_returns=4, top_reason_share=0.75, top_reason="OTHER"), CFG).points == 10
    )


def test_mismatch_history_one_versus_many():
    assert mismatch_history(feats(mismatch_count=0), CFG) is None
    assert mismatch_history(feats(mismatch_count=1), CFG).points == 10
    assert mismatch_history(feats(mismatch_count=2), CFG).points == 25


def test_short_return_window_needs_three_returns():
    assert short_return_window(feats(total_returns=2, avg_return_window=0.5), CFG) is None
    assert short_return_window(feats(total_returns=3, avg_return_window=1.9), CFG).points == 15
    assert short_return_window(feats(total_returns=3, avg_return_window=2.0), CFG) is None


def test_category_rule_needs_concentration_and_evidence():
    assert high_return_categories(feats(total_returns=1, high_risk_category_share=1.0), CFG) is None
    assert high_return_categories(feats(total_returns=3, high_risk_category_share=0.5), CFG) is None
    assert high_return_categories(feats(total_returns=3, high_risk_category_share=0.67), CFG).points == 10


def test_returns_after_high_rating():
    assert returns_after_high_rating(feats(returned_high_rating_count=1), CFG) is None
    assert returns_after_high_rating(feats(returned_high_rating_count=2), CFG).points == 5


def test_rising_return_rate():
    assert rising_return_rate(feats(return_rate_trend=None, returns_last_90d=5), CFG) is None
    assert rising_return_rate(feats(return_rate_trend=3.0, returns_last_90d=2), CFG) is None
    assert rising_return_rate(feats(return_rate_trend=3.0, returns_last_90d=3), CFG).points == 10


def test_disabled_rule_never_fires():
    cfg = CFG.model_copy(deep=True)
    cfg.rules.mismatch_history.enabled = False
    assert mismatch_history(feats(mismatch_count=5), cfg) is None


# ---- Engine -------------------------------------------------------------------------


def test_levels_follow_thresholds():
    assert [classify(s, CFG) for s in (0, 40, 41, 70, 71, 100)] == [
        "LOW",
        "LOW",
        "MEDIUM",
        "MEDIUM",
        "HIGH",
        "HIGH",
    ]


def test_customer_with_no_orders_scores_zero_with_note():
    r = score_customer(feats(), CFG)
    assert r.risk_score == 0 and r.risk_level == "LOW" and not r.requires_manual_review
    assert "not enough history" in r.notes[0]


def test_customer_with_no_returns_is_low():
    r = score_customer(build(8, []), CFG)
    assert r.risk_score == 0 and r.risk_factors == []
    assert "No returns on record." in r.notes


def test_single_return_is_not_penalised():
    r = score_customer(build(1, [ret(window=0, code="OTHER", text=None, category="Fashion")]), CFG)
    assert r.risk_score == 0


def test_low_risk_frequent_but_explained_returner():
    returns = [ret(days_ago=40 * i + 5, window=6, category="Fashion") for i in range(4)]
    r = score_customer(build(12, returns), CFG)
    assert r.risk_level == "LOW"


def test_medium_risk_customer():
    returns = [ret(days_ago=100 + i * 20, window=4, code="NOT_WORKING", text=None) for i in range(4)]
    r = score_customer(
        build(9, returns), CFG
    )  # ratio 44%: 30, vague 4: 15, repeated reason: 10 -> group cap 25
    assert r.risk_score == 55
    assert r.risk_level == "MEDIUM"
    reasons_total = sum(f.contribution for f in r.risk_factors if f.group == "return_reasons")
    assert reasons_total == 25


def test_high_risk_customer_requires_review_and_explains_every_point():
    returns = [
        ret(
            days_ago=5 + i * 10,
            window=1,
            code="OTHER",
            text=None,
            mismatch=i < 2,
            category="Fashion",
            rating=5,
        )
        for i in range(6)
    ]
    r = score_customer(build(8, returns), CFG)
    assert r.risk_level == "HIGH" and r.requires_manual_review
    total = sum(f.contribution for f in r.risk_factors)
    assert r.risk_score == min(100, total)
    if total > 100:
        assert any("capped at 100" in n for n in r.notes)
    assert all(f.description for f in r.risk_factors)


def test_correlated_volume_rules_cannot_exceed_group_cap():
    returns = [ret(days_ago=i + 1) for i in range(9)]
    r = score_customer(build(10, returns), CFG)
    volume = [f for f in r.risk_factors if f.group == "return_volume"]
    assert sum(f.contribution for f in volume) == CFG.group_caps.return_volume
    assert {f.rule_id for f in volume} == {"very_high_return_ratio", "high_return_frequency"}
    assert any("cap reached" in f.description for f in volume)


def test_score_never_exceeds_100():
    cfg = CFG.model_copy(deep=True)
    for g in ("return_volume", "return_reasons", "item_mismatch", "return_timing", "behaviour"):
        setattr(cfg.group_caps, g, 100)
    for name in type(cfg.rules).model_fields:
        getattr(cfg.rules, name).points = 60
    returns = [
        ret(days_ago=i + 1, window=0, code="OTHER", text=None, mismatch=True, category="Fashion", rating=5)
        for i in range(9)
    ] + [ret(days_ago=200)]
    r = score_customer(build(10, returns), cfg)
    assert r.risk_score == 100
