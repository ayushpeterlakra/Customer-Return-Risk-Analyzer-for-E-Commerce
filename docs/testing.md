# Testing report

All results below come from real runs on 24 Nov 2026 (Python 3.13, Node 22, PostgreSQL 16).

| Suite | Command | Result |
| --- | --- | --- |
| Backend unit (scoring rules, features, engine) | `pytest tests/unit` | 27 passed |
| Backend health/config | `pytest tests/test_health.py` | 5 passed |
| Backend integration (API + real PostgreSQL) | `pytest tests/integration` | 17 passed |
| **Backend total** | `pytest -q` | **49 passed** |
| Backend lint | `ruff check .` | clean |
| Frontend unit (formatters, components, Customers page) | `npm test` | 11 passed |
| Frontend lint / type-check / build | `npm run lint`, `npm run build` | clean |
| End-to-end (real browser, real API) | `npm run e2e` | 10 of 10 steps passed, 0 console errors |

## What the tests cover

- **Scoring:** every rule at and around its threshold, disabled rules, group caps, clamping to 100, low/medium/high customers, no orders, no returns, a single return, missing delivery dates, returns before delivery, more returns than orders.
- **Database consistency:** a fresh Alembic migration, seeded data checked so every return belongs to its own customer's delivered order and is dated on or after delivery; the database rejects a return on another customer's order and a score of 101.
- **API:** pagination, sorting, each filter, 404/409/422 error envelopes, assessment shape matching the spec, score history growth, analytics totals agreeing with each other, date-range validation, review workflow and audit trail, CSV export without emails, all-or-nothing import, rules save/validation/reset with rescoring, ML endpoints with and without a model.
- **End to end:** overview cards and charts, date presets, customer search/filters/sort/pagination, CSV export, customer detail with ML run and rescore, review status change visible in the audit trail, monitoring filter, analytics granularity toggle and ML metrics, rejected import, and the mobile menu with no horizontal scrolling.

## Bugs found and fixed during testing

| Found by | Problem | Fix |
| --- | --- | --- |
| Unit test | Factor contributions could add to more than the clamped score with no explanation | Engine adds a note when the total is capped at 100 |
| E2E | "Export CSV (all)" sent `risk_level=` and got a 400 | Export accepts `risk_level=ALL` |
| E2E | Two quick filter changes could overwrite each other in the URL | Filters use functional URL updates |
| Visual check | Customer "since" date showed the seed date | Seed writes each synthetic customer's sign-up date |
| Visual check | Return history product column wrapped badly | Minimum column widths |
| Lint | Ref read during render in the data hook | Ref updated in an effect |

## Performance

Measured locally on the seeded database (300 customers, ~2,000 orders): rescoring all 300 customers took 0.6 s; the customer table, summary, daily trend and high-risk endpoints each answered in 9–14 ms. Aggregations run in SQL (`GROUP BY`, `DISTINCT ON`), not Python loops.
