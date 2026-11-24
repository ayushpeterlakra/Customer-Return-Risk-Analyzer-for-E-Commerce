# API reference

Interactive docs: http://localhost:8000/docs (Swagger) · Schema: [`openapi.json`](openapi.json) · Postman: import [`api.postman_collection.json`](api.postman_collection.json) (variables `base_url`, `customer_id`). Regenerate both with `python -m scripts.export_api_docs`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /api/health | API and database status |
| GET | /api/customers | Table: `page`, `page_size` (≤100), `search`, `risk_level`, `min_score`, `min_return_ratio`, `category`, `sort` (risk_score, return_ratio, total_returns, total_orders, last_return_date, name, customer_id), `order` |
| GET | /api/customers/{customer_id} | Profile, totals, latest assessment, review status, category breakdown |
| GET | /api/customers/{customer_id}/orders | Order history (paginated) |
| GET | /api/customers/{customer_id}/returns | Return history with vague/mismatch flags (paginated) |
| POST | /api/risk/assess/{customer_id} | Score now, store, return the assessment (201) |
| POST | /api/risk/assess-all | Rescore everyone |
| GET | /api/risk/{customer_id} | Latest assessment |
| GET | /api/risk/{customer_id}/history | All stored scores |
| GET | /api/risk/high-risk | HIGH customers with top factors and review status (`review_status` filter) |
| GET | /api/risk/summary | Counts by level, average score |
| GET | /api/analytics/summary | Summary cards (`date_from`, `date_to`) |
| GET | /api/analytics/returns-by-category | Bar chart data (date range) |
| GET | /api/analytics/risk-distribution | Donut data |
| GET | /api/analytics/return-trends | `granularity=day|week`, date range; gaps filled with zeros |
| GET | /api/analytics/return-ratio-distribution | Customers per 10% band |
| GET | /api/analytics/return-reasons | Reason counts, vague vs explained (date range) |
| PATCH | /api/reviews/{customer_id} | Change status (`review_status`, `review_notes`, `updated_by`); 409 if unchanged |
| GET | /api/reviews | Current review status per customer |
| GET | /api/reviews/{customer_id} | Audit trail, newest first |
| POST | /api/ml/predict | Model probability (503 if no model) |
| GET | /api/ml/metrics | Stored evaluation metrics (404 if not trained) |
| POST | /api/data/import | Multipart CSV, all-or-nothing, then rescore; 422 lists errors by line |
| GET | /api/data/import/template | Empty CSV with required columns |
| GET | /api/data/export/flagged-customers | CSV, `risk_level` (LOW, MEDIUM, HIGH, ALL; default HIGH), `min_score`. No emails. |
| GET / PUT | /api/settings/scoring-rules | Read or save a new rules version (PUT rescores) |
| POST | /api/settings/scoring-rules/reset | Restore default rules and rescore |

**Errors** always use `{"error": {"code", "message", "details"}}`. 400 bad input, 404 not found, 409 conflict, 413 file too large, 422 validation, 503 model unavailable; 500 never exposes a stack trace.

**Import CSV columns:** `customer_id, customer_name, customer_email, order_id, product_id, product_name, category, order_date, delivery_date, order_amount, order_status, customer_rating, return_id, reason_code, reason_text, return_date, mismatch_flag, refund_amount, return_status`. One row per order; return columns are blank when the order was not returned.
