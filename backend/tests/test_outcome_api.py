from fastapi.testclient import TestClient
from app.main import app
from app.models.outcome import OutcomeStatus
from app.database import SessionLocal

client = TestClient(app)

def _get_completed_transfer():
    # 1. Create
    res = client.post("/api/transfers/from-recommendation", json={"sku_id": "YOG-001", "source_store_id": "STORE_A"})
    if res.status_code != 200:
        return None
    t_id = res.json()["transfer_id"]
    
    # Push to completed
    client.post(f"/api/transfers/{t_id}/approve")
    client.post(f"/api/transfers/{t_id}/assign")
    client.post(f"/api/transfers/{t_id}/pickup")
    client.post(f"/api/transfers/{t_id}/start-transit")
    client.post(f"/api/transfers/{t_id}/deliver")
    res = client.post(f"/api/transfers/{t_id}/complete")
    return res.json()

def _teardown_inventory(qty: int):
    db = SessionLocal()
    from app.models.inventory import Inventory
    source_inv = db.query(Inventory).filter(Inventory.sku_id == "YOG-001", Inventory.store_id == "STORE_A").first()
    dest_inv = db.query(Inventory).filter(Inventory.sku_id == "YOG-001", Inventory.store_id == "STORE_B").first()
    if source_inv and dest_inv:
        source_inv.quantity += qty
        dest_inv.quantity -= qty
        db.commit()
    db.close()

def test_outcome_api_flow():
    transfer_data = _get_completed_transfer()
    if not transfer_data:
        return
        
    t_id = transfer_data["transfer_id"]
    qty = transfer_data["quantity"]
    
    try:
        # 1. Create Outcome
        res = client.post(f"/api/outcomes/from-transfer/{t_id}")
        assert res.status_code == 200
        outcome = res.json()
        o_id = outcome["outcome_id"]
        assert outcome["outcome_status"] == OutcomeStatus.PENDING.value
        
        # 2. Record Sales
        res = client.post(f"/api/outcomes/{o_id}/record-sales", json={"actual_units_sold": qty})
        assert res.status_code == 200
        assert res.json()["outcome_status"] == OutcomeStatus.RECORDED.value
        
        # 3. Record Financials
        res = client.post(f"/api/outcomes/{o_id}/record-financials", json={
            "actual_recovered_value": 7000.0,
            "actual_logistics_cost": 300.0,
            "actual_handling_cost": 50.0
        })
        assert res.status_code == 200
        
        # 4. Finalize
        res = client.post(f"/api/outcomes/{o_id}/finalize")
        assert res.status_code == 200
        final_outcome = res.json()
        assert final_outcome["outcome_status"] == OutcomeStatus.FINALIZED.value
        assert final_outcome["metrics"]["recovery_variance"] is not None
        
        # 5. Fetch
        res = client.get(f"/api/outcomes/{o_id}")
        assert res.status_code == 200
        
        # 6. List
        res = client.get(f"/api/outcomes?sku_id=YOG-001")
        assert res.status_code == 200
        assert len(res.json()) > 0
        
        # 7. Summary
        res = client.get("/api/outcomes/summary")
        assert res.status_code == 200
        assert res.json()["total_completed_transfers"] > 0
        
    finally:
        _teardown_inventory(qty)
