import csv
import io

from sqlalchemy import func, select, text

from app.db import session_factory


def test_seed_is_consistent(seeded):
    s = seeded["summary"]
    assert s["customers"] == 120 and s["orders"] > 0 and s["returns"] > 0
    with session_factory()() as db:
        # Every return belongs to a valid order of the same customer, dated on/after delivery.
        bad = db.execute(
            text("""
            SELECT count(*) FROM returns r JOIN orders o ON o.id = r.order_id
            WHERE o.customer_id <> r.customer_id OR o.delivery_date IS NULL OR r.return_date < o.delivery_date
               OR r.days_to_return <> (r.return_date - o.delivery_date)""")
        ).scalar()
        assert bad == 0
        out_of_range = db.execute(
            text("SELECT count(*) FROM risk_assessments WHERE risk_score NOT BETWEEN 0 AND 100")
        )
        assert out_of_range.scalar() == 0


def test_database_rejects_inconsistent_rows(seeded):
    import pytest
    from sqlalchemy.exc import IntegrityError

    with session_factory()() as db:
        order = db.execute(
            text("SELECT id, customer_id FROM orders WHERE order_status='DELIVERED' LIMIT 1")
        ).one()
        other = db.execute(
            text("SELECT id FROM customers WHERE id <> :c LIMIT 1"), {"c": order.customer_id}
        ).scalar()
        with pytest.raises(IntegrityError):
            db.execute(
                text("""INSERT INTO returns (return_id, order_id, customer_id, reason_code, return_date,
                days_to_return, mismatch_flag, refund_amount, return_status)
                VALUES ('RETX', :o, :c, 'OTHER', '2026-01-01', 1, false, 0, 'REQUESTED')"""),
                {"o": order.id, "c": other},
            )
        db.rollback()
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "UPDATE risk_assessments SET risk_score = 101 "
                    "WHERE id = (SELECT min(id) FROM risk_assessments)"
                )
            )
        db.rollback()


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["database"] == "ok"


def test_customer_list_pagination_and_sort(client):
    r = client.get("/api/customers", params={"page_size": 10, "sort": "risk_score", "order": "desc"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 120 and len(body["items"]) == 10 and body["pages"] == 12
    scores = [i["risk_score"] for i in body["items"]]
    assert scores == sorted(scores, reverse=True)
    assert "email" not in body["items"][0]


def test_customer_filters(client):
    high = client.get("/api/customers", params={"min_score": 71, "page_size": 100}).json()["items"]
    assert all(i["risk_score"] >= 71 for i in high)
    ratio = client.get("/api/customers", params={"min_return_ratio": 0.3, "page_size": 100}).json()["items"]
    assert all(i["return_percentage"] > 30 for i in ratio)
    medium = client.get("/api/customers", params={"risk_level": "MEDIUM", "page_size": 100}).json()["items"]
    assert all(i["risk_level"] == "MEDIUM" for i in medium)
    found = client.get("/api/customers", params={"search": "CUST0007"}).json()["items"]
    assert [i["customer_id"] for i in found] == ["CUST0007"]


def test_invalid_query_returns_422_envelope(client):
    r = client.get("/api/customers", params={"page_size": 1000})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_customer_detail_orders_returns(client):
    cid = client.get("/api/customers", params={"page_size": 1}).json()["items"][0]["customer_id"]
    detail = client.get(f"/api/customers/{cid}").json()
    assert detail["latest_assessment"]["customer_id"] == cid
    orders = client.get(f"/api/customers/{cid}/orders").json()
    returns = client.get(f"/api/customers/{cid}/returns").json()
    assert orders["total"] >= detail["total_orders"]
    assert returns["total"] >= detail["total_returns"]
    assert client.get("/api/customers/NOPE").status_code == 404


def test_assessment_matches_spec_shape_and_history_grows(client):
    cid = client.get("/api/customers", params={"page_size": 1}).json()["items"][0]["customer_id"]
    before = len(client.get(f"/api/risk/{cid}/history").json())
    r = client.post(f"/api/risk/assess/{cid}")
    assert r.status_code == 201
    a = r.json()
    for key in ("customer_id", "risk_score", "risk_level", "risk_factors", "requires_manual_review"):
        assert key in a
    assert a["requires_manual_review"] == (a["risk_level"] == "HIGH")
    assert all({"factor", "contribution", "description"} <= set(f) for f in a["risk_factors"])
    assert len(client.get(f"/api/risk/{cid}/history").json()) == before + 1


def test_risk_summary_and_high_risk(client):
    summary = client.get("/api/risk/summary").json()
    assert summary["total_assessed"] == 120
    high = client.get("/api/risk/high-risk").json()
    high_count = next(level["count"] for level in summary["levels"] if level["risk_level"] == "HIGH")
    assert high["total"] == high_count
    assert all(i["review_status"] == "PENDING_REVIEW" or i["review_status"] for i in high["items"])


def test_analytics_endpoints(client):
    s = client.get("/api/analytics/summary").json()
    assert s["total_customers"] == 120
    assert s["high_risk_customers"] + s["medium_risk_customers"] + s["low_risk_customers"] == 120
    cats = client.get("/api/analytics/returns-by-category").json()
    assert sum(c["returns"] for c in cats) == s["total_returns"]
    dist = client.get("/api/analytics/risk-distribution").json()
    assert sum(d["count"] for d in dist) == 120
    trends = client.get("/api/analytics/return-trends", params={"granularity": "week"}).json()
    assert sum(t["returns"] for t in trends) == s["total_returns"]
    buckets = client.get("/api/analytics/return-ratio-distribution").json()
    assert len(buckets) == 10
    ranged = client.get(
        "/api/analytics/summary", params={"date_from": "2026-09-01", "date_to": "2026-11-15"}
    ).json()
    assert ranged["total_returns"] <= s["total_returns"]
    assert (
        client.get(
            "/api/analytics/summary", params={"date_from": "2026-10-01", "date_to": "2026-09-01"}
        ).status_code
        == 400
    )


def test_review_workflow_and_audit_trail(client):
    cid = "CUST0001"
    trail_before = client.get(f"/api/reviews/{cid}").json()
    current = trail_before[0]["review_status"] if trail_before else None
    target = "UNDER_INVESTIGATION" if current != "UNDER_INVESTIGATION" else "REVIEWED"
    r = client.patch(
        f"/api/reviews/{cid}",
        json={"review_status": target, "review_notes": "Checking photos", "updated_by": "Test Admin"},
    )
    assert r.status_code == 200
    assert r.json()["previous_status"] == current
    again = client.patch(f"/api/reviews/{cid}", json={"review_status": target, "updated_by": "Test Admin"})
    assert again.status_code == 409
    blank = client.patch(f"/api/reviews/{cid}", json={"review_status": "ESCALATED", "updated_by": "  "})
    assert blank.status_code == 422
    trail = client.get(f"/api/reviews/{cid}").json()
    assert len(trail) == len(trail_before) + 1 and trail[0]["review_status"] == target
    listed = client.get("/api/reviews", params={"review_status": target}).json()["items"]
    assert any(i["customer_id"] == cid for i in listed)


def test_export_has_no_emails(client):
    r = client.get("/api/data/export/flagged-customers", params={"risk_level": "MEDIUM"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert "email" not in rows[0] if rows else True
    assert all(row["risk_level"] == "MEDIUM" for row in rows)


def test_import_rejects_bad_rows_atomically(client):
    from app.services.data_service import IMPORT_COLUMNS

    with session_factory()() as db:
        orders_before = db.scalar(text("SELECT count(*) FROM orders"))
    header = ",".join(IMPORT_COLUMNS)
    good = (
        "CUSTX01,Demo Person,demo.person@example.com,ORDX0001,PRODX01,Demo Lamp,Home & Kitchen,2026-10-01,"
        "2026-10-03,40.00,DELIVERED,5,RETX0001,DEFECTIVE,,2026-10-04,false,40.00,REFUNDED"
    )
    bad = (
        "CUSTX01,Demo Person,demo.person@example.com,ORDX0002,PRODX01,Demo Lamp,Home & Kitchen,2026-10-05,"
        "2026-10-07,30.00,DELIVERED,,RETX0002,DEFECTIVE,,2026-10-06,false,30.00,REFUNDED"
    )
    r = client.post("/api/data/import", files={"file": ("x.csv", f"{header}\n{good}\n{bad}\n", "text/csv")})
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["field"] == "return_date"
    with session_factory()() as db:
        assert db.scalar(text("SELECT count(*) FROM orders")) == orders_before

    r = client.post("/api/data/import", files={"file": ("x.csv", f"{header}\n{good}\n", "text/csv")})
    assert r.status_code == 200, r.text
    assert r.json()["imported"] == {"customers": 1, "products": 1, "orders": 1, "returns": 1}
    assert client.get("/api/customers/CUSTX01").json()["total_returns"] == 1


def test_settings_save_and_rescore(client):
    current = client.get("/api/settings/scoring-rules").json()
    cfg = current["config"]
    cfg["rules"]["mismatch_history"]["enabled"] = False
    r = client.put("/api/settings/scoring-rules", json={"config": cfg, "updated_by": "Test Admin"})
    assert r.status_code == 200
    version = r.json()["config"]["version"]
    a = client.get("/api/risk/CUST0002").json()
    assert a["config_version"] == version
    assert all(f["rule_id"] != "mismatch_history" for f in a["risk_factors"])
    bad = dict(cfg, levels={"low_max": 80, "medium_max": 50})
    assert (
        client.put("/api/settings/scoring-rules", json={"config": bad, "updated_by": "x"}).status_code == 422
    )
    reset = client.post("/api/settings/scoring-rules/reset")
    assert reset.status_code == 200
    assert reset.json()["config"]["rules"]["mismatch_history"]["enabled"] is True


def test_ml_endpoints_without_model_degrade_gracefully(client):
    assert client.get("/api/ml/metrics").status_code == 404
    r = client.post("/api/ml/predict", json={"customer_id": "CUST0001"})
    assert r.status_code == 503
    assert client.post("/api/ml/predict", json={}).status_code == 422


def test_ml_train_and_predict(client, seeded, monkeypatch):
    import scripts.train as train

    monkeypatch.setattr(train, "LABELS_PATH", seeded["labels"])
    train.main()
    metrics = client.get("/api/ml/metrics").json()
    assert set(metrics["models"]) == {"logistic_regression", "decision_tree"}
    for m in metrics["models"].values():
        cm = m["confusion_matrix"]
        assert sum(cm.values()) == metrics["dataset"]["test"]
    r = client.post("/api/ml/predict", json={"customer_id": "CUST0001", "model": "decision_tree"})
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["probability_suspicious_pattern"] <= 1 and body["model"] == "decision_tree"
    raw = client.post(
        "/api/ml/predict",
        json={
            "features": {"total_orders": 10, "total_returns": 7, "mismatch_count": 3, "vague_reason_count": 5}
        },
    )
    assert raw.status_code == 200 and raw.json()["rule_based_score"] is None


def test_counts_match_database(seeded):
    from app.models import Return

    with session_factory()() as db:
        assert db.scalar(select(func.count(Return.id))) >= seeded["summary"]["returns"]
