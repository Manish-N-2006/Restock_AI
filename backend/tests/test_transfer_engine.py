from app.database import SessionLocal
from app.services.transfer_engine import (
    create_transfer_from_recommendation,
    approve_transfer,
    assign_transfer,
    mark_pickup_pending,
    start_transfer,
    mark_delivered,
    complete_transfer,
    cancel_transfer
)
from app.models.transfer import TransferStatus, TransferOrder
from app.models.inventory import Inventory
import pytest
from fastapi import HTTPException

def test_full_transfer_lifecycle():
    db = SessionLocal()
    try:
        # Create
        order = create_transfer_from_recommendation(db, "YOG-001", "STORE_A")
        assert order.status == TransferStatus.CREATED
        assert order.sku_id == "YOG-001"
        assert order.source_store_id == "STORE_A"
        
        # Approve
        order = approve_transfer(db, order.transfer_id)
        assert order.status == TransferStatus.APPROVED
        
        # Check reservation
        inv = db.query(Inventory).filter(Inventory.sku_id == "YOG-001", Inventory.store_id == "STORE_A").first()
        assert inv.reserved_quantity == order.quantity
        
        # Assign
        order = assign_transfer(db, order.transfer_id)
        assert order.status == TransferStatus.ASSIGNED
        
        # Pickup
        order = mark_pickup_pending(db, order.transfer_id)
        assert order.status == TransferStatus.PICKUP_PENDING
        
        # Transit
        order = start_transfer(db, order.transfer_id)
        assert order.status == TransferStatus.IN_TRANSIT
        
        # Deliver
        order = mark_delivered(db, order.transfer_id)
        assert order.status == TransferStatus.DELIVERED
        
        # Record initial target inventory if exists
        target_inv = db.query(Inventory).filter(Inventory.sku_id == "YOG-001", Inventory.store_id == order.destination_store_id).first()
        initial_target_qty = target_inv.quantity if target_inv else 0
        initial_source_qty = inv.quantity
        
        # Complete
        order = complete_transfer(db, order.transfer_id)
        assert order.status == TransferStatus.COMPLETED
        
        # Check actual inventory changes
        db.refresh(inv)
        assert inv.quantity == initial_source_qty - order.quantity
        assert inv.reserved_quantity == 0
        
        target_inv_after = db.query(Inventory).filter(Inventory.sku_id == "YOG-001", Inventory.store_id == order.destination_store_id).first()
        assert target_inv_after.quantity == initial_target_qty + order.quantity
        
        # Restore state so other tests pass
        inv.quantity += order.quantity
        target_inv_after.quantity -= order.quantity
        db.commit()
        
    finally:
        db.close()

def test_transfer_cancellation():
    db = SessionLocal()
    try:
        order = create_transfer_from_recommendation(db, "YOG-001", "STORE_A")
        order = approve_transfer(db, order.transfer_id)
        
        inv = db.query(Inventory).filter(Inventory.sku_id == "YOG-001", Inventory.store_id == "STORE_A").first()
        assert inv.reserved_quantity == order.quantity
        
        # Cancel
        order = cancel_transfer(db, order.transfer_id)
        assert order.status == TransferStatus.CANCELLED
        
        db.refresh(inv)
        assert inv.reserved_quantity == 0
    finally:
        db.close()

def test_invalid_state_transition():
    db = SessionLocal()
    try:
        order = create_transfer_from_recommendation(db, "YOG-001", "STORE_A")
        # Cannot deliver from created
        with pytest.raises(HTTPException):
            mark_delivered(db, order.transfer_id)
    finally:
        db.close()
