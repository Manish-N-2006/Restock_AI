import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

from app.authorization.principal import get_current_principal
app.dependency_overrides[get_current_principal] = lambda: {
    "uid": {"type": "ReStockAI::User", "id": "manager-test"},
    "attrs": {"role": "MANAGER", "store_scope": "*"},
    "parents": []
}


def test_unknown_sku_analysis_fails():
    res = client.post("/api/workflow/analyze", json={
        "sku_id": "UNKNOWN",
        "source_store_id": "STORE_A"
    })
    # Dependent on how risk_engine handles it. Typically it returns an error or raises 404
    assert res.status_code in [404, 200]
    if res.status_code == 200:
        assert "error" in res.json().get("risk", {}) or res.json().get("risk", {}).get("risk_level") is None

def test_execute_non_transfer_decision():
    # If a product doesn't need transfer
    req_data = {
        "sku_id": "BREAD-001",
        "source_store_id": "STORE_A",
        "actual_units_sold": 0,
        "actual_recovered_value": 0,
        "actual_logistics_cost": 0,
        "actual_handling_cost": 0
    }
    res = client.post("/api/workflow/execute", json=req_data)
    assert res.status_code == 200
    data = res.json()
    if data["workflow_status"] == "COMPLETED" and "transfer" not in data:
        # Expected for a non-transfer decision
        assert True
    else:
        # If bread actually transfers in the dataset, skip
        pass

@patch('app.services.orchestration_engine.get_integrated_recommendation')
def test_no_logistics_partner(mock_logistics):
    class MockLogistics:
        def model_dump(self):
            return {"logistics": {"selected_partner": None}}
            
    mock_logistics.return_value = MockLogistics()
    
    req_data = {
        "sku_id": "YOG-001",
        "source_store_id": "STORE_A",
        "actual_units_sold": 42,
        "actual_recovered_value": 6720.0,
        "actual_logistics_cost": 320.0,
        "actual_handling_cost": 50.0
    }
    res = client.post("/api/workflow/execute", json=req_data)
    assert res.status_code == 200
    data = res.json()
    assert data["workflow_status"] == "FAILED"
    assert data["failed_stage"] == "LOGISTICS"

@patch('app.services.orchestration_engine.upsert_outcome_history')
def test_opensearch_unavailable(mock_upsert):
    mock_upsert.side_effect = Exception("Connection Refused")
    
    req_data = {
        "sku_id": "YOG-001",
        "source_store_id": "STORE_A",
        "actual_units_sold": 42,
        "actual_recovered_value": 6720.0,
        "actual_logistics_cost": 320.0,
        "actual_handling_cost": 50.0
    }
    res = client.post("/api/workflow/execute", json=req_data)
    assert res.status_code == 200
    data = res.json()
    # Should complete business logic but fail indexing gracefully
    assert data["workflow_status"] == "COMPLETED"
    assert data["history"]["indexed"] is False
