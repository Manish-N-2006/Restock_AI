from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from typing import List, Optional
import uuid
from datetime import datetime

from ..models.inventory import Inventory
from ..models.store import Store
from ..models.transfer import TransferOrder, TransferEvent, TransferStatus
from ..schemas.decision import RecoveryActionType
from .logistics_engine import get_integrated_recommendation

def validate_transition(current_status: TransferStatus, next_status: TransferStatus) -> bool:
    valid_transitions = {
        TransferStatus.CREATED: [TransferStatus.APPROVED, TransferStatus.CANCELLED],
        TransferStatus.APPROVED: [TransferStatus.ASSIGNED, TransferStatus.CANCELLED],
        TransferStatus.ASSIGNED: [TransferStatus.PICKUP_PENDING, TransferStatus.CANCELLED],
        TransferStatus.PICKUP_PENDING: [TransferStatus.IN_TRANSIT, TransferStatus.CANCELLED],
        TransferStatus.IN_TRANSIT: [TransferStatus.DELIVERED, TransferStatus.FAILED],
        TransferStatus.DELIVERED: [TransferStatus.COMPLETED, TransferStatus.FAILED],
        TransferStatus.COMPLETED: [],
        TransferStatus.CANCELLED: [],
        TransferStatus.FAILED: []
    }
    return next_status in valid_transitions.get(current_status, [])

def create_transfer_event(db: Session, transfer_id: str, from_status: Optional[TransferStatus], to_status: TransferStatus, event_type: str, message: str):
    event = TransferEvent(
        transfer_id=transfer_id,
        from_status=from_status,
        to_status=to_status,
        event_type=event_type,
        message=message
    )
    db.add(event)

def generate_transfer_id() -> str:
    # Stable human readable ID TR-XXXXXX
    unique_part = str(uuid.uuid4()).split('-')[0].upper()
    return f"TR-{unique_part}"

def create_transfer_from_recommendation(db: Session, sku_id: str, source_store_id: str, partner_id: Optional[str] = None) -> TransferOrder:
    rec = get_integrated_recommendation(db, sku_id, source_store_id)
    
    if rec.decision.selected_action != RecoveryActionType.TRANSFER:
        raise HTTPException(status_code=400, detail="Recommendation is not a transfer.")
        
    if not rec.transfer_still_viable and not partner_id:
        raise HTTPException(status_code=400, detail="Transfer is not economically viable after logistics adjustment.")
        
    source_inv = db.query(Inventory).filter(Inventory.sku_id == sku_id, Inventory.store_id == source_store_id).first()
    
    if source_inv.quantity - source_inv.reserved_quantity < rec.decision.recommended_quantity:
        raise HTTPException(status_code=400, detail="Insufficient available inventory at source store.")
        
    # Override logic for manual partner selection
    selected_partner = rec.logistics.selected_partner
    delivery_cost = rec.logistics.delivery_cost
    eta_minutes = rec.logistics.eta_minutes
    logistics_adjusted_net_recovery = rec.logistics_adjusted_net_recovery
    
    if partner_id:
        from .logistics_engine import evaluate_logistics_options
        options = evaluate_logistics_options(
            db, sku_id, source_store_id, rec.decision.selected_destination_store_id, rec.decision.recommended_quantity
        )
        partner_match = next((p for p in options.options if p.partner_id == partner_id), None)
        if partner_match:
            selected_partner = partner_match
            delivery_cost = partner_match.estimated_delivery_cost
            eta_minutes = partner_match.average_eta_minutes
            logistics_adjusted_net_recovery = rec.decision.expected_net_recovery - delivery_cost
    
    transfer_id = generate_transfer_id()
    
    order = TransferOrder(
        transfer_id=transfer_id,
        sku_id=sku_id,
        product_name=source_inv.product_name,
        source_store_id=source_store_id,
        destination_store_id=rec.decision.selected_destination_store_id,
        quantity=rec.decision.recommended_quantity,
        status=TransferStatus.CREATED,
        logistics_partner_id=selected_partner.partner_id,
        logistics_partner_name=selected_partner.partner_name,
        distance_km=selected_partner.distance_km,
        estimated_delivery_cost=delivery_cost,
        estimated_eta_minutes=eta_minutes,
        expected_net_recovery=rec.decision.expected_net_recovery,
        logistics_adjusted_net_recovery=logistics_adjusted_net_recovery
    )
    
    db.add(order)
    create_transfer_event(db, transfer_id, None, TransferStatus.CREATED, "ORDER_CREATED", f"Transfer order {transfer_id} created from approved ReStockAI recommendation.")
    
    db.commit()
    db.refresh(order)
    return order

def create_manual_transfer(db: Session, sku_id: str, source_store_id: str, destination_store_id: str, quantity: int) -> TransferOrder:
    if source_store_id == destination_store_id:
        raise HTTPException(status_code=400, detail="Source and destination stores cannot be the same.")
        
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Transfer quantity must be greater than zero.")
        
    source_inv = db.query(Inventory).filter(Inventory.sku_id == sku_id, Inventory.store_id == source_store_id).first()
    if not source_inv:
        raise HTTPException(status_code=404, detail="SKU not found at source store.")
        
    if source_inv.quantity - source_inv.reserved_quantity < quantity:
        raise HTTPException(status_code=400, detail="Insufficient available inventory at source store.")
        
    dest_store = db.query(Store).filter(Store.store_id == destination_store_id).first()
    if not dest_store:
        raise HTTPException(status_code=404, detail="Destination store not found.")
        
    transfer_id = generate_transfer_id()
    
    order = TransferOrder(
        transfer_id=transfer_id,
        sku_id=sku_id,
        product_name=source_inv.product_name,
        source_store_id=source_store_id,
        destination_store_id=destination_store_id,
        quantity=quantity,
        status=TransferStatus.CREATED
    )
    
    db.add(order)
    create_transfer_event(db, transfer_id, None, TransferStatus.CREATED, "ORDER_CREATED", f"Manual transfer order {transfer_id} created.")
    
    db.commit()
    db.refresh(order)
    return order

def approve_transfer(db: Session, transfer_id: str) -> TransferOrder:
    order = db.query(TransferOrder).filter(TransferOrder.transfer_id == transfer_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Transfer order not found.")
        
    if not validate_transition(order.status, TransferStatus.APPROVED):
        raise HTTPException(status_code=400, detail=f"Cannot transition from {order.status.value} to APPROVED.")
        
    source_inv = db.query(Inventory).filter(Inventory.sku_id == order.sku_id, Inventory.store_id == order.source_store_id).first()
    
    if source_inv.quantity - source_inv.reserved_quantity < order.quantity:
        raise HTTPException(status_code=400, detail="Insufficient available inventory for reservation.")
        
    try:
        source_inv.reserved_quantity += order.quantity
        order.status = TransferStatus.APPROVED
        order.approved_at = datetime.utcnow()
        
        create_transfer_event(db, transfer_id, TransferStatus.CREATED, TransferStatus.APPROVED, "ORDER_APPROVED", f"Transfer approved and {order.quantity} units reserved at {order.source_store_id}.")
        db.commit()
        db.refresh(order)
        return order
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error during approval.")

def assign_transfer(db: Session, transfer_id: str) -> TransferOrder:
    order = db.query(TransferOrder).filter(TransferOrder.transfer_id == transfer_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Transfer order not found.")
        
    if not validate_transition(order.status, TransferStatus.ASSIGNED):
        raise HTTPException(status_code=400, detail=f"Cannot transition from {order.status.value} to ASSIGNED.")
        
    if not order.logistics_partner_name:
        raise HTTPException(status_code=400, detail="No logistics partner associated with this transfer.")
        
    order.status = TransferStatus.ASSIGNED
    order.assigned_at = datetime.utcnow()
    
    create_transfer_event(db, transfer_id, TransferStatus.APPROVED, TransferStatus.ASSIGNED, "PARTNER_ASSIGNED", f"{order.logistics_partner_name} assigned to transfer.")
    db.commit()
    db.refresh(order)
    return order

def mark_pickup_pending(db: Session, transfer_id: str) -> TransferOrder:
    order = db.query(TransferOrder).filter(TransferOrder.transfer_id == transfer_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Transfer order not found.")
        
    if not validate_transition(order.status, TransferStatus.PICKUP_PENDING):
        raise HTTPException(status_code=400, detail=f"Cannot transition from {order.status.value} to PICKUP_PENDING.")
        
    order.status = TransferStatus.PICKUP_PENDING
    
    create_transfer_event(db, transfer_id, TransferStatus.ASSIGNED, TransferStatus.PICKUP_PENDING, "PICKUP_PENDING", f"Pickup requested from {order.source_store_id}.")
    db.commit()
    db.refresh(order)
    return order

def start_transfer(db: Session, transfer_id: str) -> TransferOrder:
    order = db.query(TransferOrder).filter(TransferOrder.transfer_id == transfer_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Transfer order not found.")
        
    if not validate_transition(order.status, TransferStatus.IN_TRANSIT):
        raise HTTPException(status_code=400, detail=f"Cannot transition from {order.status.value} to IN_TRANSIT.")
        
    order.status = TransferStatus.IN_TRANSIT
    order.picked_up_at = datetime.utcnow()
    order.in_transit_at = datetime.utcnow()
    
    create_transfer_event(db, transfer_id, TransferStatus.PICKUP_PENDING, TransferStatus.IN_TRANSIT, "IN_TRANSIT", f"{order.quantity} units picked up and shipment is in transit.")
    db.commit()
    db.refresh(order)
    return order

def mark_delivered(db: Session, transfer_id: str) -> TransferOrder:
    order = db.query(TransferOrder).filter(TransferOrder.transfer_id == transfer_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Transfer order not found.")
        
    if not validate_transition(order.status, TransferStatus.DELIVERED):
        raise HTTPException(status_code=400, detail=f"Cannot transition from {order.status.value} to DELIVERED.")
        
    order.status = TransferStatus.DELIVERED
    order.delivered_at = datetime.utcnow()
    
    create_transfer_event(db, transfer_id, TransferStatus.IN_TRANSIT, TransferStatus.DELIVERED, "DELIVERED", f"Shipment delivered to {order.destination_store_id}.")
    db.commit()
    db.refresh(order)
    return order

def complete_transfer(db: Session, transfer_id: str) -> TransferOrder:
    order = db.query(TransferOrder).filter(TransferOrder.transfer_id == transfer_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Transfer order not found.")
        
    if not validate_transition(order.status, TransferStatus.COMPLETED):
        raise HTTPException(status_code=400, detail=f"Cannot transition from {order.status.value} to COMPLETED.")
        
    source_inv = db.query(Inventory).filter(Inventory.sku_id == order.sku_id, Inventory.store_id == order.source_store_id).first()
    
    if not source_inv or source_inv.reserved_quantity < order.quantity or source_inv.quantity < order.quantity:
        raise HTTPException(status_code=500, detail="Inventory reservation inconsistency detected. Cannot complete.")
        
    try:
        # 1. Decrease source quantity and reservation
        source_inv.quantity -= order.quantity
        source_inv.reserved_quantity -= order.quantity
        
        # 2. Increase destination quantity
        dest_inv = db.query(Inventory).filter(Inventory.sku_id == order.sku_id, Inventory.store_id == order.destination_store_id).first()
        if dest_inv:
            dest_inv.quantity += order.quantity
        else:
            # Create new inventory record at destination
            new_inv = Inventory(
                sku_id=source_inv.sku_id,
                product_name=source_inv.product_name,
                store_id=order.destination_store_id,
                quantity=order.quantity,
                cost_price=source_inv.cost_price,
                selling_price=source_inv.selling_price,
                expiry_date=source_inv.expiry_date,
                temperature_class=source_inv.temperature_class,
                created_at=datetime.utcnow(),
                return_allowed=source_inv.return_allowed,
                supplier_return_value=source_inv.supplier_return_value,
                reserved_quantity=0,
                daily_sales_7d=0.0 # Starts at 0 for new location
            )
            db.add(new_inv)
            
        # 3. Mark transfer complete
        order.status = TransferStatus.COMPLETED
        order.completed_at = datetime.utcnow()
        
        create_transfer_event(db, transfer_id, TransferStatus.DELIVERED, TransferStatus.COMPLETED, "COMPLETED", f"Inventory transfer completed. {order.source_store_id} decreased by {order.quantity} units and {order.destination_store_id} increased by {order.quantity} units.")
        
        db.commit()
        db.refresh(order)
        
        # Phase 9: Index the completed transfer into OpenSearch.
        # This is wrapped gracefully in the repository, so it won't crash or rollback the transaction if OpenSearch is down.
        try:
            from ..opensearch.repository import index_transfer_history
            index_transfer_history(order)
        except Exception:
            pass # Failsafe against absolute catastrophic import/invocation failure
            
        return order
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database transaction failed during transfer completion.")

def cancel_transfer(db: Session, transfer_id: str) -> TransferOrder:
    order = db.query(TransferOrder).filter(TransferOrder.transfer_id == transfer_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Transfer order not found.")
        
    if not validate_transition(order.status, TransferStatus.CANCELLED):
        raise HTTPException(status_code=400, detail=f"Cannot transition from {order.status.value} to CANCELLED.")
        
    old_status = order.status
    
    try:
        # If it was approved (and thus reserved), release the reservation
        if order.status in [TransferStatus.APPROVED, TransferStatus.ASSIGNED, TransferStatus.PICKUP_PENDING]:
            source_inv = db.query(Inventory).filter(Inventory.sku_id == order.sku_id, Inventory.store_id == order.source_store_id).first()
            if source_inv and source_inv.reserved_quantity >= order.quantity:
                source_inv.reserved_quantity -= order.quantity
                
        order.status = TransferStatus.CANCELLED
        order.cancelled_at = datetime.utcnow()
        
        create_transfer_event(db, transfer_id, old_status, TransferStatus.CANCELLED, "CANCELLED", "Transfer cancelled and inventory reservation released.")
        
        db.commit()
        db.refresh(order)
        return order
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database transaction failed during cancellation.")

def get_transfer(db: Session, transfer_id: str) -> TransferOrder:
    order = db.query(TransferOrder).filter(TransferOrder.transfer_id == transfer_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Transfer order not found.")
    return order

def list_transfers(db: Session, status: Optional[str] = None, sku_id: Optional[str] = None, source_store_id: Optional[str] = None, destination_store_id: Optional[str] = None) -> List[TransferOrder]:
    query = db.query(TransferOrder)
    
    if status:
        try:
            status_enum = TransferStatus(status)
            query = query.filter(TransferOrder.status == status_enum)
        except ValueError:
            pass # Ignore invalid status filter
            
    if sku_id:
        query = query.filter(TransferOrder.sku_id == sku_id)
    if source_store_id:
        query = query.filter(TransferOrder.source_store_id == source_store_id)
    if destination_store_id:
        query = query.filter(TransferOrder.destination_store_id == destination_store_id)
        
    return query.all()

def get_transfer_summary(db: Session) -> dict:
    transfers = db.query(TransferOrder).all()
    
    summary = {
        "total_transfers": len(transfers),
        "created": sum(1 for t in transfers if t.status == TransferStatus.CREATED),
        "approved": sum(1 for t in transfers if t.status == TransferStatus.APPROVED),
        "assigned": sum(1 for t in transfers if t.status == TransferStatus.ASSIGNED),
        "pickup_pending": sum(1 for t in transfers if t.status == TransferStatus.PICKUP_PENDING),
        "in_transit": sum(1 for t in transfers if t.status == TransferStatus.IN_TRANSIT),
        "delivered": sum(1 for t in transfers if t.status == TransferStatus.DELIVERED),
        "completed": sum(1 for t in transfers if t.status == TransferStatus.COMPLETED),
        "cancelled": sum(1 for t in transfers if t.status == TransferStatus.CANCELLED),
        "failed": sum(1 for t in transfers if t.status == TransferStatus.FAILED),
        "total_units_transferred": sum(t.quantity for t in transfers if t.status == TransferStatus.COMPLETED),
        "total_estimated_logistics_cost": sum(t.estimated_delivery_cost for t in transfers if t.estimated_delivery_cost is not None and t.status != TransferStatus.CANCELLED),
        "total_expected_net_recovery": sum(t.expected_net_recovery for t in transfers if t.expected_net_recovery is not None and t.status != TransferStatus.CANCELLED)
    }
    return summary
