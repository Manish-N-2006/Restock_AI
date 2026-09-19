from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ReStockAI"}

def test_evaluate_recovery_invalid_quantity():
    response = client.post(
        "/api/recovery/evaluate",
        json={
            "sku_id": "YOG-001",
            "quantity": 0,
            "source_store_id": "STORE_A",
            "action": "transfer"
        }
    )
    assert response.status_code == 400
    assert "Quantity must be greater than 0" in response.json()["detail"]
