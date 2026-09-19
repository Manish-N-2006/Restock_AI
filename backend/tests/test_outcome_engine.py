import pytest
from fastapi import HTTPException
from app.database import SessionLocal
from app.models.transfer import TransferStatus, TransferOrder
from app.models.outcome import OutcomeStatus, Outcome
from app.services.transfer_engine import (
    create_transfer_from_recommendation,
    approve_transfer,
    assign_transfer,
    mark_pickup_pending,
    start_transfer,
    mark_delivered,
    complete_transfer
)
from app.services.outcome_engine import (
    create_outcome_from_transfer,
    record_actual_sales,
    record_actual_financials,
    finalize_outcome
)

def _setup_completed_transfer(db):
    # Make sure we have a fresh transfer
    order = create_transfer_from_recommendation(db, "YOG-001", "STORE_A")
    order = approve_transfer(db, order.transfer_id)
    order = assign_transfer(db, order.transfer_id)
    order = mark_pickup_pending(db, order.transfer_id)
    order = start_transfer(db, order.transfer_id)
    order = mark_delivered(db, order.transfer_id)
    order = complete_transfer(db, order.transfer_id)
    return order

def _teardown_completed_transfer(db, order):
    from app.models.inventory import Inventory
    source_inv = db.query(Inventory).filter(Inventory.sku_id == "YOG-001", Inventory.store_id == "STORE_A").first()
    dest_inv = db.query(Inventory).filter(Inventory.sku_id == "YOG-001", Inventory.store_id == "STORE_B").first()
    if source_inv and dest_inv:
        source_inv.quantity += order.quantity
        dest_inv.quantity -= order.quantity
        db.commit()

def test_outcome_lifecycle():
    db = SessionLocal()
    order = None
    try:
        order = _setup_completed_transfer(db)
        
        # 1. Create Outcome
        outcome = create_outcome_from_transfer(db, order.transfer_id)
        assert outcome.outcome_status == OutcomeStatus.PENDING
        assert outcome.transferred_quantity == order.quantity
        assert outcome.predicted_units_sold == order.quantity
        assert outcome.predicted_net_recovery == order.expected_net_recovery
        
        # Prevent duplicates
        with pytest.raises(HTTPException) as exc:
            create_outcome_from_transfer(db, order.transfer_id)
        assert exc.value.status_code == 400
        
        # 2. Record Sales
        outcome = record_actual_sales(db, outcome.outcome_id, actual_units_sold=outcome.transferred_quantity - 2)
        assert outcome.outcome_status == OutcomeStatus.RECORDED
        assert outcome.actual_unsold_units == 2
        
        # Prevent exceeding transferred quantity
        with pytest.raises(HTTPException):
            record_actual_sales(db, outcome.outcome_id, actual_units_sold=outcome.transferred_quantity + 1)
            
        # 3. Record Financials
        # Let's say we sold them slightly cheaper, log cost was higher
        actual_rec_val = outcome.predicted_recovered_value - 200
        outcome = record_actual_financials(db, outcome.outcome_id, actual_rec_val, outcome.predicted_logistics_cost + 50, outcome.predicted_handling_cost)
        
        expected_actual_net = actual_rec_val - (outcome.predicted_logistics_cost + 50) - outcome.predicted_handling_cost
        assert outcome.actual_net_recovery == expected_actual_net
        
        # 4. Finalize
        outcome = finalize_outcome(db, outcome.outcome_id)
        assert outcome.outcome_status == OutcomeStatus.FINALIZED
        assert outcome.recovery_variance == outcome.actual_net_recovery - outcome.predicted_net_recovery
        assert outcome.unit_sales_variance == -2
        assert outcome.logistics_cost_variance == 50
        
        # 5. Verify Immutability
        with pytest.raises(HTTPException):
            record_actual_sales(db, outcome.outcome_id, actual_units_sold=0)
            
    finally:
        if order:
            _teardown_completed_transfer(db, order)
        db.close()

def test_create_outcome_uncompleted_transfer():
    db = SessionLocal()
    order = None
    try:
        order = create_transfer_from_recommendation(db, "YOG-001", "STORE_A")
        
        with pytest.raises(HTTPException) as exc:
            create_outcome_from_transfer(db, order.transfer_id)
        assert exc.value.status_code == 400
        
    finally:
        db.close()
