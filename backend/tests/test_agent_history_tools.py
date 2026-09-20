import pytest
from unittest.mock import patch
from app.agent.tools import search_historical_recovery

def test_search_historical_recovery_tool_success():
    mock_res = {
        "total": 1,
        "results": [
            {
                "transfer_id": "TR-123",
                "sku_id": "YOG-001",
                "outcome": {"actual_net_recovery": 100.0}
            }
        ]
    }
    with patch('app.agent.tools.search_history', return_value=mock_res):
        res = search_historical_recovery(query="yogurt", sku_id="YOG-001")
        assert res["total"] == 1
        assert res["results"][0]["transfer_id"] == "TR-123"
        
def test_search_historical_recovery_tool_unavailable():
    mock_res = {"error": "OpenSearch is unavailable", "total": 0, "results": []}
    with patch('app.agent.tools.search_history', return_value=mock_res):
        res = search_historical_recovery(query="yogurt")
        assert res["error"] == "OpenSearch is unavailable"
        assert res["total"] == 0
