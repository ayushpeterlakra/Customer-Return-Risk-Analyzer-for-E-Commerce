from fastapi.testclient import TestClient

from app import db
from app.main import app

client = TestClient(app)


def test_health_reports_ok_when_database_reachable(monkeypatch):
    monkeypatch.setattr("app.routers.health.check_database", lambda: (True, None))
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["database_error"] is None


def test_health_reports_degraded_when_database_down(monkeypatch):
    monkeypatch.setattr("app.routers.health.check_database", lambda: (False, "OperationalError"))
    body = client.get("/api/health").json()
    assert body["status"] == "degraded"
    assert body["database"] == "unavailable"
    assert body["database_error"] == "OperationalError"


def test_unknown_route_uses_error_envelope():
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_404"


def test_cors_allows_frontend_origin():
    response = client.options(
        "/api/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_check_database_returns_false_for_bad_url(monkeypatch):
    from sqlalchemy import create_engine

    bad = create_engine("postgresql+psycopg://x:y@127.0.0.1:1/none", connect_args={"connect_timeout": 1})
    monkeypatch.setattr(db, "get_engine", lambda: bad)
    ok, error = db.check_database()
    assert ok is False
    assert error
