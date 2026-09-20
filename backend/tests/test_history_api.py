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


def test_get_health_unavailable():
    with patch('app.routers.history.get_opensearch_client', return_value=None):
        response = client.get("/api/history/health")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False

def test_search_api_unavailable():
    with patch('app.routers.history.search_history', return_value={"error": "OpenSearch is unavailable"}):
        response = client.get("/api/history/search?q=yogurt")
        assert response.status_code == 503

def test_search_api_success():
    mock_res = {
        "total": 1,
        "results": [
            {
                "transfer_id": "TR-111",
                "sku_id": "SKU-1",
                "source_store_id": "S1",
                "destination_store_id": "S2",
                "decision": {"action": "TRANSFER"},
                "outcome": {"actual_net_recovery": 100.0, "recovery_accuracy_percentage": 95.0, "actual_units_sold": 10}
            }
        ]
    }
    with patch('app.routers.history.search_history', return_value=mock_res):
        response = client.get("/api/history/search?sku_id=SKU-1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["results"][0]["transfer_id"] == "TR-111"

def test_get_transfer_not_found():
    with patch('app.routers.history.get_history_by_transfer_id', return_value=None):
        response = client.get("/api/history/transfer/TR-UNKNOWN")
        assert response.status_code == 404

def test_get_summary_success():
    mock_res = {
        "total_indexed_transfers": 10,
        "total_finalized_outcomes": 5,
        "total_units_moved": 100,
        "total_actual_net_recovery": 1000.0,
        "transfer_count_by_action": {"TRANSFER": 10},
        "transfer_count_by_partner": {"P1": 10}
    }
    with patch('app.routers.history.get_history_summary', return_value=mock_res):
        response = client.get("/api/history/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_indexed_transfers"] == 10
