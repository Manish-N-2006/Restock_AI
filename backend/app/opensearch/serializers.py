from typing import Dict, Any, Optional
from datetime import datetime
from ..models.transfer import TransferOrder
from ..models.outcome import Outcome, OutcomeStatus

def serialize_transfer_to_document(transfer: TransferOrder) -> Dict[str, Any]:
    """
    Serializes a completed TransferOrder into an OpenSearch document.
    """
    return {
        "document_id": transfer.transfer_id,
        "document_type": "transfer_history",
        "transfer_id": transfer.transfer_id,
        "sku_id": transfer.sku_id,
        "product_name": transfer.product_name,
        "source_store_id": transfer.source_store_id,
        "destination_store_id": transfer.destination_store_id,
        "quantity": transfer.quantity,
        
        "decision": {
            "action": "TRANSFER",
            "expected_net_recovery": transfer.expected_net_recovery
        },
        
        "logistics": {
            "partner_id": None, # Will populate if available in the model
            "partner_name": transfer.logistics_partner_name,
            "estimated_cost": transfer.estimated_delivery_cost,
            "estimated_eta_minutes": transfer.estimated_eta_minutes
        },
        
        "outcome": {
            "outcome_status": "PENDING", # Default until outcome is recorded
        },
        
        "created_at": transfer.created_at.isoformat() if transfer.created_at else None,
        "completed_at": transfer.completed_at.isoformat() if transfer.completed_at else None,
        "outcome_finalized_at": None,
        "explanation": f"Transfer of {transfer.quantity} units of {transfer.sku_id} from {transfer.source_store_id} to {transfer.destination_store_id}."
    }

def serialize_outcome_to_document(outcome: Outcome, transfer: Optional[TransferOrder] = None) -> Dict[str, Any]:
    """
    Updates or creates an OpenSearch document from an Outcome.
    If transfer is provided, it incorporates transfer details.
    """
    doc = {
        "document_id": outcome.transfer_id,
        "document_type": "transfer_history",
        "transfer_id": outcome.transfer_id,
        "sku_id": outcome.sku_id,
        "source_store_id": outcome.source_store_id,
        "destination_store_id": outcome.destination_store_id,
        "quantity": outcome.transferred_quantity,
        
        "outcome": {
            "outcome_status": outcome.outcome_status.value,
            "predicted_units_sold": outcome.predicted_units_sold,
            "actual_units_sold": outcome.actual_units_sold,
            "actual_recovered_value": outcome.actual_recovered_value,
            "actual_logistics_cost": outcome.actual_logistics_cost,
            "actual_handling_cost": outcome.actual_handling_cost,
            "actual_net_recovery": outcome.actual_net_recovery,
            "recovery_variance": outcome.recovery_variance,
            "sell_through_rate": outcome.sell_through_rate,
            "recovery_accuracy_percentage": outcome.recovery_accuracy_percentage
        },
        
        "outcome_finalized_at": outcome.finalized_at.isoformat() if outcome.finalized_at else None
    }
    
    # If a finalized outcome has events, take the last one as the explanation
    if outcome.outcome_status == OutcomeStatus.FINALIZED and outcome.events:
        doc["explanation"] = outcome.events[-1].message
        
    if transfer:
        doc["product_name"] = transfer.product_name
        doc["decision"] = {
            "action": "TRANSFER",
            "expected_net_recovery": transfer.expected_net_recovery
        }
        doc["logistics"] = {
            "partner_id": None,
            "partner_name": transfer.logistics_partner_name,
            "estimated_cost": transfer.estimated_delivery_cost,
            "estimated_eta_minutes": transfer.estimated_eta_minutes
        }
        doc["created_at"] = transfer.created_at.isoformat() if transfer.created_at else None
        doc["completed_at"] = transfer.completed_at.isoformat() if transfer.completed_at else None

    return doc
