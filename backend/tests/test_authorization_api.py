import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.authorization.principal import get_current_principal

client = TestClient(app)

def test_authorization_check_manager():
    app.dependency_overrides[get_current_principal] = lambda: {
        "uid": {"type": "ReStockAI::User", "id": "manager-test"},
        "attrs": {"role": "MANAGER", "store_scope": "*"},
        "parents": []
    }
    
    response = client.post("/api/authorization/check", json={
        "action": "CREATE_TRANSFER",
        "resource_type": "Transfer",
        "resource_id": "tr-1"
    })
    
    assert response.status_code == 200
    assert response.json()["allowed"] is True
    assert response.json()["principal_role"] == "MANAGER"

def test_authorization_check_viewer_denied():
    app.dependency_overrides[get_current_principal] = lambda: {
        "uid": {"type": "ReStockAI::User", "id": "viewer-test"},
        "attrs": {"role": "VIEWER", "store_scope": "*"},
        "parents": []
    }
    
    response = client.post("/api/authorization/check", json={
        "action": "CREATE_TRANSFER",
        "resource_type": "Transfer",
        "resource_id": "tr-1"
    })
    
    assert response.status_code == 200
    assert response.json()["allowed"] is False
    assert response.json()["principal_role"] == "VIEWER"

def test_api_rejection_for_viewer():
    app.dependency_overrides[get_current_principal] = lambda: {
        "uid": {"type": "ReStockAI::User", "id": "viewer-test"},
        "attrs": {"role": "VIEWER", "store_scope": "*"},
        "parents": []
    }
    
    # Trying to create a transfer as a viewer should return 403
    response = client.post("/api/transfers", json={
        "sku_id": "SKU-123",
        "source_store_id": "STORE_A",
        "destination_store_id": "STORE_B",
        "quantity": 10
    })
    
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]
    
def test_api_success_for_manager():
    app.dependency_overrides[get_current_principal] = lambda: {
        "uid": {"type": "ReStockAI::User", "id": "manager-test"},
        "attrs": {"role": "MANAGER", "store_scope": "*"},
        "parents": []
    }
    
    # Needs valid sku_id etc. Since this is an E2E test it will hit the DB.
    # It might fail with 400 Bad Request if the SKU doesn't exist, but it shouldn't fail with 403.
    response = client.post("/api/transfers", json={
        "sku_id": "SKU-TEST-NON-EXISTENT",
        "source_store_id": "STORE_A",
        "destination_store_id": "STORE_B",
        "quantity": 10
    })
    
    assert response.status_code != 403
