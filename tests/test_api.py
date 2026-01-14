from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root() -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "message" in r.json()


def test_health() -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_risk_score() -> None:
    payload = {"income": 1000, "debt": 100, "age": 30, "credit_history_months": 36}
    r = client.post("/api/v1/risk/score", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["risk_score"] <= 1.0
    assert body["risk_label"] in {"low", "medium", "high"}
    assert isinstance(body["explanation"], str) and body["explanation"]


def test_chat() -> None:
    r = client.post("/api/v1/chat", json={"message": "Power BI tích hợp sao?"})
    assert r.status_code == 200
    assert "answer" in r.json()
