import json
import pytest
from infrastructure.sam.src.handlers.analyze import lambda_handler

def test_lambda_handler_missing_body():
    event = {}
    response = lambda_handler(event, None)
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "Missing sku_id" in body["error"]

def test_lambda_handler_invalid_json():
    event = {"body": "{ invalid json "}
    response = lambda_handler(event, None)
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "Invalid JSON" in body["error"]

def test_lambda_handler_missing_fields():
    event = {"body": json.dumps({"sku_id": "YOG-001"})}
    response = lambda_handler(event, None)
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "Missing sku_id or source_store_id" in body["error"]

def test_lambda_handler_unknown_sku():
    event = {"body": json.dumps({"sku_id": "UNKNOWN", "source_store_id": "STORE_A"})}
    response = lambda_handler(event, None)
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert "No inventory found" in body["error"]

def test_lambda_handler_success_transfer():
    # Test an item that will likely result in a TRANSFER (assuming YOG-001 at STORE_A)
    event = {"body": json.dumps({"sku_id": "YOG-001", "source_store_id": "STORE_A"})}
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    
    # Assert fields are present based on handler implementation
    assert body["sku_id"] == "YOG-001"
    assert body["source_store_id"] == "STORE_A"
    assert "risk" in body
    assert "demand" in body
    assert "decision" in body
    assert "logistics" in body
    
    if body["decision"]["selected_action"] == "TRANSFER":
        assert body["execution_ready"] is True
        assert body["logistics"] is not None
    else:
        assert body["execution_ready"] is False
        assert body["logistics"] is None
