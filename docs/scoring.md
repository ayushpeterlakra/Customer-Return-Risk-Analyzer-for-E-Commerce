# Risk scoring algorithm

The rule-based engine (`backend/app/scoring/`) gives each customer a score from 0 to 100, a level, and a list of factors that explains every point. Defaults live in `backend/scoring_config.yaml`; the Settings page saves new versions to the database.

| Score | Level | Action |
| --- | --- | --- |
| 0–40 | LOW | none |
| 41–70 | MEDIUM | watch |
| 71–100 | HIGH | `requires_manual_review = true`, queued as Pending review |

## Features

| Feature | Definition |
| --- | --- |
| total_orders | orders not CANCELLED |
| total_returns | returns not REJECTED |
| return_ratio | total_returns / total_orders (capped at 1.0, flagged as a data issue if higher) |
| returns_last_90d | returns in the 90 days before the scoring date |
| return_rate_trend | monthly rate in the last 90 days ÷ monthly rate in the 90–365 day window |
| vague_reason_count | returns with a vague code (DEFECTIVE, NOT_WORKING, OTHER) **and** fewer than 15 characters of explanation |
| top_reason_share | share of returns using the single most common reason |
| avg_return_window | mean days from delivery to return (negative or missing windows excluded and reported) |
| high_risk_category_share | share of returns in categories whose return rate is 5+ points above the store rate |
| mismatch_count | returns where the item sent back did not match the item ordered |
| returned_high_rating_count | returned orders the customer rated 4–5 stars |

## Rules and group caps

| Group (cap) | Rule | Fires when | Points |
| --- | --- | --- | --- |
| Return volume (35) | Very high return ratio | ratio > 60% and ≥ 5 orders | 35 (replaces the next rule) |
| | High return ratio | ratio > 40% and ≥ 3 orders | 30 |
| | High return frequency | ≥ 4 returns in 90 days | 15 |
| Return reasons (25) | Vague reasons | ≥ 3 vague returns | 15 |
| | Repeated identical reason | same reason on ≥ 70% of ≥ 4 returns | 10 |
| Item mismatch (25) | Mismatch history | 1 incident: 10, 2+: 25 | 10/25 |
| Return timing (15) | Short return window | average < 2 days over ≥ 3 returns | 15 |
| Behaviour (20) | High-return categories | ≥ 60% of ≥ 3 returns in high-return categories | 10 |
| | Returned items rated highly | ≥ 2 returned items rated 4–5 | 5 |
| | Rising return rate | trend ≥ 2× with ≥ 3 recent returns | 10 |

Within a group, the strongest rule counts first and points stop at the cap; a capped factor says so in its description ("Counted 0 of 15 points: return volume cap reached"). The total is clamped to 100, with a note when it is.

### Changes from the starting logic and why

- **Caps on correlated rules** so a heavy returner is not charged three times for the same behaviour.
- **Minimum evidence** on every rule: one order with one fast return scores 0, not 30+.
- **Category weight 20 → 10**, and it measures where returns concentrate, not what a customer buys.
- **Vague = code + no explanation.** "Defective: left earbud stops charging" is not vague.
- **Configurable and versioned.** Each assessment stores `config_version` and the feature snapshot.

### Responsible use

A score is a prompt for a human to look at the history. It never labels a customer as fraudulent, and the UI says so on every risk view.

## Example output (real, from the seeded demo database)

```json
{
  "customer_id": "CUST0046",
  "risk_score": 95,
  "risk_level": "HIGH",
  "risk_factors": [
    {"factor": "Very high return ratio", "contribution": 35, "description": "Returned 11 of 14 orders (79%), above the 60% threshold."},
    {"factor": "Vague return reasons", "contribution": 15, "description": "3 returns gave a vague reason with no explanation (limit 2)."},
    {"factor": "Short return window", "contribution": 15, "description": "Average 1.1 days from delivery to return, under the 2-day threshold."}
  ],
  "requires_manual_review": true
}
```

(Shortened: the full response also lists the mismatch, category and trend factors, the capped factors, `notes`, `features`, `config_version` and `assessed_at`.)
