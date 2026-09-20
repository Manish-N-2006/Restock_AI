import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from ..models.transfer import TransferOrder, TransferStatus
from ..models.outcome import Outcome, OutcomeEvent, OutcomeStatus
from ..schemas.outcome import OutcomeResponse, OutcomePredictionSnapshot, OutcomeActualsSnapshot, OutcomeMetricsSnapshot

def get_outcome(db: Session, outcome_id: str) -> Outcome:
    outcome = db.query(Outcome).filter(Outcome.outcome_id == outcome_id).first()
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found.")
    return outcome

def _log_event(db: Session, outcome_id: str, event_type: str, message: str):
    evt = OutcomeEvent(
        outcome_id=outcome_id,
        event_type=event_type,
        message=message
    )
    db.add(evt)

def create_outcome_from_transfer(db: Session, transfer_id: str) -> Outcome:
    transfer = db.query(TransferOrder).filter(TransferOrder.transfer_id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found.")
    
    if transfer.status != TransferStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Transfer is not COMPLETED.")
        
    existing = db.query(Outcome).filter(Outcome.transfer_id == transfer_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Outcome already exists for this transfer.")
        
    outcome_id = f"OUT-{uuid.uuid4().hex[:8].upper()}"
    
    # Deriving predicted units sold: Since transfer logic bounds transfer quantity 
    # to the destination's capacity, the prediction inherently expects all transferred units to sell.
    predicted_units_sold = transfer.quantity
    
    # In Phase 3, expected_net_recovery is net of logistics and handling.
    # Logistics and Handling costs were stored in TransferOrder snapshot.
    predicted_logistics_cost = transfer.estimated_delivery_cost or 0.0
    predicted_net_recovery = transfer.expected_net_recovery or 0.0
    
    # We must deduce predicted handling cost. Phase 3 uses BASE_HANDLING = 10 * quantity
    predicted_handling_cost = transfer.quantity * 10.0
    
    # Recovered value (Gross) = Net Recovery + Logistics Cost + Handling Cost
    predicted_recovered_value = predicted_net_recovery + predicted_logistics_cost + predicted_handling_cost

    outcome = Outcome(
        outcome_id=outcome_id,
        transfer_id=transfer_id,
        sku_id=transfer.sku_id,
        source_store_id=transfer.source_store_id,
        destination_store_id=transfer.destination_store_id,
        transferred_quantity=transfer.quantity,
        
        predicted_units_sold=predicted_units_sold,
        predicted_recovered_value=predicted_recovered_value,
        predicted_logistics_cost=predicted_logistics_cost,
        predicted_handling_cost=predicted_handling_cost,
        predicted_net_recovery=predicted_net_recovery,
        
        outcome_status=OutcomeStatus.PENDING
    )
    db.add(outcome)
    
    _log_event(db, outcome_id, "OUTCOME_CREATED", f"Outcome tracking initialized for transfer {transfer_id}.")
    
    db.commit()
    db.refresh(outcome)
    return outcome

def record_actual_sales(db: Session, outcome_id: str, actual_units_sold: int) -> Outcome:
    outcome = get_outcome(db, outcome_id)
    
    if outcome.outcome_status == OutcomeStatus.FINALIZED:
        raise HTTPException(status_code=400, detail="Cannot modify finalized outcome.")
        
    if actual_units_sold > outcome.transferred_quantity:
        raise HTTPException(status_code=400, detail="Actual units sold cannot exceed transferred quantity.")
        
    outcome.actual_units_sold = actual_units_sold
    outcome.actual_unsold_units = outcome.transferred_quantity - actual_units_sold
    
    if outcome.outcome_status == OutcomeStatus.PENDING:
        outcome.outcome_status = OutcomeStatus.RECORDED
        
    _log_event(db, outcome_id, "SALES_RECORDED", f"Recorded {actual_units_sold} actual units sold.")
    
    db.commit()
    db.refresh(outcome)
    return outcome

def record_actual_financials(db: Session, outcome_id: str, recovered_value: float, logistics_cost: float, handling_cost: float) -> Outcome:
    outcome = get_outcome(db, outcome_id)
    
    if outcome.outcome_status == OutcomeStatus.FINALIZED:
        raise HTTPException(status_code=400, detail="Cannot modify finalized outcome.")
        
    outcome.actual_recovered_value = recovered_value
    outcome.actual_logistics_cost = logistics_cost
    outcome.actual_handling_cost = handling_cost
    
    outcome.actual_net_recovery = recovered_value - logistics_cost - handling_cost
    
    if outcome.outcome_status == OutcomeStatus.PENDING:
        outcome.outcome_status = OutcomeStatus.RECORDED
        
    _log_event(db, outcome_id, "FINANCIALS_RECORDED", f"Recorded financials: Net Recovery = {outcome.actual_net_recovery}.")
    
    db.commit()
    db.refresh(outcome)
    return outcome

def finalize_outcome(db: Session, outcome_id: str) -> Outcome:
    outcome = get_outcome(db, outcome_id)
    
    if outcome.outcome_status == OutcomeStatus.FINALIZED:
        raise HTTPException(status_code=400, detail="Outcome is already finalized.")
        
    # Validation
    if outcome.actual_units_sold is None:
        raise HTTPException(status_code=400, detail="Actual sales must be recorded before finalization.")
    if outcome.actual_recovered_value is None or outcome.actual_logistics_cost is None or outcome.actual_handling_cost is None:
        raise HTTPException(status_code=400, detail="Actual financials must be recorded before finalization.")
        
    # Calculate derived metrics
    outcome.recovery_variance = outcome.actual_net_recovery - outcome.predicted_net_recovery
    
    if outcome.predicted_net_recovery != 0:
        outcome.recovery_percentage = round((outcome.actual_net_recovery / outcome.predicted_net_recovery) * 100.0, 2)
        
        abs_err = abs(outcome.actual_net_recovery - outcome.predicted_net_recovery)
        acc = 100.0 - (abs_err / abs(outcome.predicted_net_recovery) * 100.0)
        outcome.recovery_accuracy_percentage = round(max(0.0, acc), 2)
    else:
        outcome.recovery_percentage = None
        outcome.recovery_accuracy_percentage = None
        
    outcome.unit_sales_variance = outcome.actual_units_sold - outcome.predicted_units_sold
    outcome.logistics_cost_variance = outcome.actual_logistics_cost - outcome.predicted_logistics_cost
    
    if outcome.transferred_quantity > 0:
        outcome.sell_through_rate = round((outcome.actual_units_sold / outcome.transferred_quantity) * 100.0, 2)
    else:
        outcome.sell_through_rate = 0.0
        
    outcome.outcome_status = OutcomeStatus.FINALIZED
    outcome.finalized_at = datetime.utcnow()
    
    # Generate Explanation
    diff = outcome.actual_net_recovery - outcome.predicted_net_recovery
    var_str = f"exceeding the prediction by {diff}" if diff > 0 else f"resulting in a variance of {diff}"
    if diff == 0: var_str = "matching the prediction exactly"
    
    explanation = f"{outcome.actual_units_sold} of {outcome.transferred_quantity} transferred units were sold. Actual net recovery was {outcome.actual_net_recovery} compared with the predicted {outcome.predicted_net_recovery}, {var_str}."
    
    _log_event(db, outcome_id, "OUTCOME_FINALIZED", explanation)
    
    db.commit()
    db.refresh(outcome)
    
    # Phase 9: Upsert the final outcome metrics into the OpenSearch historical document.
    try:
        from ..opensearch.repository import upsert_outcome_history
        from .transfer_engine import get_transfer
        # Get transfer to enrich the outcome document
        transfer = db.query(TransferOrder).filter(TransferOrder.transfer_id == outcome.transfer_id).first()
        upsert_outcome_history(outcome, transfer)
    except Exception:
        pass
        
    return outcome

def list_outcomes(db: Session, sku_id: Optional[str] = None, transfer_id: Optional[str] = None, destination_store_id: Optional[str] = None, status: Optional[str] = None) -> List[Outcome]:
    query = db.query(Outcome)
    if sku_id:
        query = query.filter(Outcome.sku_id == sku_id)
    if transfer_id:
        query = query.filter(Outcome.transfer_id == transfer_id)
    if destination_store_id:
        query = query.filter(Outcome.destination_store_id == destination_store_id)
    if status:
        query = query.filter(Outcome.outcome_status == OutcomeStatus(status))
    
    return query.all()

def get_outcome_summary(db: Session) -> dict:
    transfers_count = db.query(TransferOrder).filter(TransferOrder.status == TransferStatus.COMPLETED).count()
    finalized_outcomes = db.query(Outcome).filter(Outcome.outcome_status == OutcomeStatus.FINALIZED).all()
    
    summary = {
        "total_completed_transfers": transfers_count,
        "total_finalized_outcomes": len(finalized_outcomes),
        "total_units_transferred": 0,
        "total_units_sold": 0,
        "total_units_unsold": 0,
        "total_recovered_value": 0.0,
        "total_actual_logistics_cost": 0.0,
        "total_actual_net_recovery": 0.0,
        "total_predicted_net_recovery": 0.0,
        "total_recovery_variance": 0.0,
        "average_recovery_accuracy": None,
        "average_sell_through_rate": None
    }
    
    if finalized_outcomes:
        accuracies = []
        sell_throughs = []
        for o in finalized_outcomes:
            summary["total_units_transferred"] += o.transferred_quantity
            summary["total_units_sold"] += o.actual_units_sold
            summary["total_units_unsold"] += o.actual_unsold_units
            summary["total_recovered_value"] += o.actual_recovered_value
            summary["total_actual_logistics_cost"] += o.actual_logistics_cost
            summary["total_actual_net_recovery"] += o.actual_net_recovery
            summary["total_predicted_net_recovery"] += o.predicted_net_recovery
            summary["total_recovery_variance"] += o.recovery_variance
            
            if o.recovery_accuracy_percentage is not None:
                accuracies.append(o.recovery_accuracy_percentage)
            if o.sell_through_rate is not None:
                sell_throughs.append(o.sell_through_rate)
                
        if accuracies:
            summary["average_recovery_accuracy"] = round(sum(accuracies) / len(accuracies), 2)
        if sell_throughs:
            summary["average_sell_through_rate"] = round(sum(sell_throughs) / len(sell_throughs), 2)
            
    return summary

def build_outcome_response(outcome: Outcome) -> OutcomeResponse:
    return OutcomeResponse(
        outcome_id=outcome.outcome_id,
        transfer_id=outcome.transfer_id,
        sku_id=outcome.sku_id,
        source_store_id=outcome.source_store_id,
        destination_store_id=outcome.destination_store_id,
        transferred_quantity=outcome.transferred_quantity,
        
        prediction=OutcomePredictionSnapshot(
            predicted_units_sold=outcome.predicted_units_sold,
            predicted_recovered_value=outcome.predicted_recovered_value,
            predicted_logistics_cost=outcome.predicted_logistics_cost,
            predicted_handling_cost=outcome.predicted_handling_cost,
            predicted_net_recovery=outcome.predicted_net_recovery
        ),
        
        actual=OutcomeActualsSnapshot(
            actual_units_sold=outcome.actual_units_sold,
            actual_unsold_units=outcome.actual_unsold_units,
            actual_recovered_value=outcome.actual_recovered_value,
            actual_logistics_cost=outcome.actual_logistics_cost,
            actual_handling_cost=outcome.actual_handling_cost,
            actual_net_recovery=outcome.actual_net_recovery
        ),
        
        metrics=OutcomeMetricsSnapshot(
            recovery_variance=outcome.recovery_variance,
            recovery_percentage=outcome.recovery_percentage,
            unit_sales_variance=outcome.unit_sales_variance,
            logistics_cost_variance=outcome.logistics_cost_variance,
            recovery_accuracy_percentage=outcome.recovery_accuracy_percentage,
            sell_through_rate=outcome.sell_through_rate
        ),
        
        outcome_status=outcome.outcome_status.value,
        outcome_recorded_at=outcome.outcome_recorded_at,
        finalized_at=outcome.finalized_at,
        events=outcome.events
    )
