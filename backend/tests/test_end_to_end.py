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


@patch('app.services.orchestration_engine.upsert_outcome_history')
def test_end_to_end_full_recovery_workflow_success(mock_upsert):
    # Execute full workflow for YOG-001 at STORE_A
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
    
    assert data["workflow_status"] == "COMPLETED"
    assert data["transfer"]["status"] == "COMPLETED"
    assert data["outcome"]["status"] == "FINALIZED"
    assert data["history"]["indexed"] is True
    
    mock_upsert.assert_called_once()
    
    transfer_id = data["transfer"]["transfer_id"]
    
    # Check Status endpoint
    status_res = client.get(f"/api/workflow/status/{transfer_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["transfer"]["status"] == "COMPLETED"
    assert status_data["outcome"]["status"] == "FINALIZED"
    
@patch('app.opensearch.repository.upsert_outcome_history')
def test_end_to_end_analysis_only(mock_upsert):
    req_data = {
        "sku_id": "YOG-001",
        "source_store_id": "STORE_A"
    }
    
    res = client.post("/api/workflow/analyze", json=req_data)
    assert res.status_code == 200
    data = res.json()
    
    assert data["sku_id"] == "YOG-001"
    assert "risk" in data
    assert "destination_matches" in data
    assert "decision" in data
    assert "logistics" in data
    
    assert mock_upsert.called is False
