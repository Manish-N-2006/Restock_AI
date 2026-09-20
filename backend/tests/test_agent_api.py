import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

from app.authorization.principal import get_current_principal
app.dependency_overrides[get_current_principal] = lambda: {
    "uid": {"type": "ReStockAI::User", "id": "manager-test"},
    "attrs": {"role": "MANAGER", "store_scope": "*"},
    "parents": []
}


@patch('app.routers.agent.ask_restock_agent')
def test_api_agent_ask(mock_ask):
    mock_ask.return_value = {
        "question": "What should I do?",
        "answer": "Transfer to Store B",
        "tools_used": ["get_inventory_risk"]
    }
    
    res = client.post("/api/agent/ask", json={"question": "What should I do?"})
    assert res.status_code == 200
    data = res.json()
    assert data["answer"] == "Transfer to Store B"
    assert "get_inventory_risk" in data["tools_used"]

@patch('app.routers.agent.analyze_inventory_with_agent')
def test_api_agent_analyze(mock_analyze):
    mock_analyze.return_value = {
        "question": "What should I do with YOG-001 at STORE_A?",
        "answer": "Transfer recommended.",
        "tools_used": []
    }
    
    res = client.get("/api/agent/analyze/YOG-001?store_id=STORE_A")
    assert res.status_code == 200
    data = res.json()
    assert "YOG-001" in data["question"]
    assert data["answer"] == "Transfer recommended."

@patch('app.routers.agent.requests.get')
def test_api_agent_health(mock_get):
    class MockResponse:
        status_code = 200
        def json(self):
            return {"models": [{"name": "llama3.1"}]}
            
    mock_get.return_value = MockResponse()
    
    res = client.get("/api/agent/health")
    assert res.status_code == 200
    data = res.json()
    assert data["configured"] is True
    assert data["available"] is True
    assert data["model_name"] == "llama3.1"
    
@patch('app.routers.agent.requests.get')
def test_api_agent_health_unavailable(mock_get):
    mock_get.side_effect = Exception("Connection refused")
    
    res = client.get("/api/agent/health")
    assert res.status_code == 200
    data = res.json()
    assert data["configured"] is True
    assert data["available"] is False
