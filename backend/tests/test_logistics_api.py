from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

from app.authorization.principal import get_current_principal
app.dependency_overrides[get_current_principal] = lambda: {
    "uid": {"type": "ReStockAI::User", "id": "manager-test"},
    "attrs": {"role": "MANAGER", "store_scope": "*"},
    "parents": []
}


def test_get_logistics_options_success():
    response = client.get("/api/logistics/options?sku_id=YOG-001&source_store_id=STORE_A&destination_store_id=STORE_B&transfer_quantity=10")
    assert response.status_code == 200
    data = response.json()
    assert data["sku_id"] == "YOG-001"
    assert data["matched"] is True
    assert len(data["options"]) > 0

def test_get_best_logistics_success():
    response = client.get("/api/logistics/best?sku_id=YOG-001&source_store_id=STORE_A&destination_store_id=STORE_B&transfer_quantity=10")
    assert response.status_code == 200
    data = response.json()
    assert data["matched"] is True
    assert data["selected_partner"] is not None
    assert data["selected_partner"]["supports_cold_chain"] is True
    
def test_get_best_logistics_not_found():
    # Provide a bad SKU
    response = client.get("/api/logistics/best?sku_id=BAD-SKU&source_store_id=STORE_A&destination_store_id=STORE_B&transfer_quantity=10")
    assert response.status_code == 200
    data = response.json()
    assert data["matched"] is False
    assert data["selected_partner"] is None

def test_get_integrated_recommendation_success():
    response = client.get("/api/logistics/recommend/YOG-001?source_store_id=STORE_A")
    assert response.status_code == 200
    data = response.json()
    assert "decision" in data
    assert "logistics" in data
    assert data["decision"]["selected_action"] == "TRANSFER"
    assert data["logistics_adjusted_net_recovery"] > 0
    assert data["transfer_still_viable"] is True

def test_get_integrated_recommendation_no_transfer():
    # Provide a SKU that triggers NO_ACTION (e.g. SNK-001 has no destinations and risk might be low or discount might win)
    # Actually SNK-001 at STORE_A triggers DISCOUNT because no destinations have capacity/demand
    response = client.get("/api/logistics/recommend/SNK-001?source_store_id=STORE_A")
    assert response.status_code == 200
    data = response.json()
    assert data["decision"]["selected_action"] == "NO_ACTION"
    assert data["logistics"] is None

def test_get_logistics_summary():
    response = client.get("/api/logistics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_logistics_partners" in data
    assert "eligible_partner_evaluations" in data
    assert data["total_logistics_partners"] > 0
