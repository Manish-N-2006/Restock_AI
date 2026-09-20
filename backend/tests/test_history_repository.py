import pytest
from unittest.mock import patch, MagicMock
from app.opensearch.repository import search_history, get_history_summary, search_similar_scenarios
from app.opensearch.serializers import serialize_transfer_to_document, serialize_outcome_to_document
from app.models.transfer import TransferOrder
from app.models.outcome import Outcome, OutcomeStatus
from datetime import datetime

def test_search_history_unavailable():
    with patch('app.opensearch.repository.get_opensearch_client', return_value=None):
        res = search_history(q="yogurt")
        assert res["total"] == 0
        assert res["error"] == "OpenSearch is unavailable"

def test_search_history_success():
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "hits": {
            "total": {"value": 1},
            "hits": [
                {"_source": {"transfer_id": "TR-123", "product_name": "Yogurt"}}
            ]
        }
    }
    
    with patch('app.opensearch.repository.get_opensearch_client', return_value=mock_client):
        res = search_history(sku_id="YOG-001")
        assert res["total"] == 1
        assert res["results"][0]["transfer_id"] == "TR-123"

def test_get_history_summary_unavailable():
    with patch('app.opensearch.repository.get_opensearch_client', return_value=None):
        res = get_history_summary()
        assert res["error"] == "OpenSearch is unavailable"

def test_serialize_transfer():
    t = TransferOrder(
        transfer_id="TR-999",
        sku_id="SKU-1",
        product_name="Product 1",
        source_store_id="S1",
        destination_store_id="S2",
        quantity=50,
        expected_net_recovery=100.0,
        created_at=datetime.utcnow()
    )
    doc = serialize_transfer_to_document(t)
    assert doc["document_id"] == "TR-999"
    assert doc["sku_id"] == "SKU-1"
    assert doc["outcome"]["outcome_status"] == "PENDING"
    assert doc["decision"]["action"] == "TRANSFER"

def test_serialize_outcome():
    o = Outcome(
        outcome_id="OUT-999",
        transfer_id="TR-999",
        sku_id="SKU-1",
        source_store_id="S1",
        destination_store_id="S2",
        transferred_quantity=50,
        outcome_status=OutcomeStatus.FINALIZED,
        actual_units_sold=48,
        actual_net_recovery=95.0,
        finalized_at=datetime.utcnow()
    )
    doc = serialize_outcome_to_document(o)
    assert doc["document_id"] == "TR-999"
    assert doc["outcome"]["outcome_status"] == "FINALIZED"
    assert doc["outcome"]["actual_units_sold"] == 48
