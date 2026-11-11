import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.decision import RecoveryActionType
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


def test_get_decision_success():
    response = client.get("/api/decision/YOG-001?store_id=STORE_A")
    assert response.status_code == 200
    data = response.json()
    assert data["sku_id"] == "YOG-001"
    assert data["store_id"] == "STORE_A"
    
    # Store A YOG-001 should recommend TRANSFER to STORE_B
    assert data["selected_action"] == RecoveryActionType.TRANSFER.value
    assert data["selected_destination_store_id"] == "STORE_B"
    assert len(data["actions"]) >= 6

def test_get_decision_not_found():
    response = client.get("/api/decision/UNKNOWN-999?store_id=STORE_A")
    assert response.status_code == 200
    data = response.json()
    assert data["selected_action"] == RecoveryActionType.NO_ACTION.value
    assert data["decision_reason"] == "Item not found."

def test_get_action_comparison():
    response = client.get("/api/decision/YOG-001/actions?store_id=STORE_A")
    assert response.status_code == 200
    data = response.json()
    assert "actions" in data
    assert len(data["actions"]) > 0

def test_get_decision_summary():
    response = client.get("/api/decision/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_at_risk_items" in data
    assert "items_with_viable_recovery" in data
    
def test_get_all_decisions():
    response = client.get("/api/decision/all")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # At least some decisions should exist in the mock dataset
    assert len(data) > 0
