import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.service import reset_auth_runtime_state

client = TestClient(app)


@pytest.fixture(autouse=True, scope="module")
def authenticated_session():
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("RESTOCKAI_DEMO_PASSWORD", "test-suite-pass")
        mp.setenv("RESTOCKAI_SESSION_SECRET", "test-suite-secret-0123456789abcdef")
        reset_auth_runtime_state()
        saved = dict(app.dependency_overrides)
        app.dependency_overrides.clear()
        res = client.post("/api/auth/login", json={"password": "test-suite-pass"})
        assert res.status_code == 200
        client.headers.update({"X-CSRF-Token": res.json()["csrf_token"]})
        try:
            yield
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(saved)
            reset_auth_runtime_state()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ReStockAI"}

def test_evaluate_recovery_invalid_quantity():
    response = client.post(
        "/api/recovery/evaluate",
        json={
            "sku_id": "YOG-001",
            "quantity": 0,
            "source_store_id": "STORE_A",
            "action": "transfer"
        }
    )
    assert response.status_code == 400
    assert "Quantity must be greater than 0" in response.json()["detail"]
