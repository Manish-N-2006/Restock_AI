import pytest
from unittest.mock import patch, MagicMock
from app.agent.service import ask_restock_agent, analyze_inventory_with_agent

@patch('app.agent.service.create_restock_agent')
def test_ask_restock_agent_success(mock_create):
    mock_agent = MagicMock()
    
    mock_result = MagicMock()
    mock_message = MagicMock()
    mock_content = MagicMock()
    mock_content.text = "Mocked answer based on tools."
    
    mock_message.content = [mock_content]
    mock_result.message = mock_message
    
    mock_agent.return_value = mock_result
    mock_create.return_value = mock_agent
    
    res = ask_restock_agent("What should I do?")
    assert res["question"] == "What should I do?"
    assert res["answer"] == "Mocked answer based on tools."

@patch('app.agent.service.create_restock_agent')
def test_ask_restock_agent_failure(mock_create):
    mock_agent = MagicMock()
    mock_agent.side_effect = Exception("Ollama connection refused")
    mock_create.return_value = mock_agent
    
    res = ask_restock_agent("What should I do?")
    assert "Ollama model cannot be reached" in res["answer"]
    assert "error_detail" in res

@patch('app.agent.service.ask_restock_agent')
def test_analyze_inventory_with_agent(mock_ask):
    mock_ask.return_value = {"question": "What should I do with YOG-001 at STORE_A?", "answer": "Analysis result.", "tools_used": []}
    
    res = analyze_inventory_with_agent("YOG-001", "STORE_A")
    assert "YOG-001" in res["question"]
    assert res["answer"] == "Analysis result."
