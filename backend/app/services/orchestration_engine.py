import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from ..database import SessionLocal
from .risk_engine import calculate_inventory_risk
from .demand_engine import find_destination_candidates
from .decision_engine import evaluate_decision
from .logistics_engine import get_integrated_recommendation
from ..models.inventory import Inventory
from .transfer_engine import (
    create_transfer_from_recommendation, approve_transfer, assign_transfer,
    mark_pickup_pending, start_transfer, mark_delivered, complete_transfer, get_transfer
)
from .outcome_engine import (
    create_outcome_from_transfer, record_actual_sales,
    record_actual_financials, finalize_outcome, get_outcome
)
from ..opensearch.repository import index_transfer_history, upsert_outcome_history
from ..models.transfer import TransferStatus
from ..models.outcome import OutcomeStatus
from ..schemas.decision import RecoveryActionType

logger = logging.getLogger(__name__)

def run_recovery_analysis(sku_id: str, source_store_id: str) -> Dict[str, Any]:
    """
    READ ONLY mode.
    Executes the analysis stages (Risk -> Demand -> Decision -> Logistics).
    """
    logger.info(f"workflow_started: analysis for {sku_id} at {source_store_id}")
    
    with SessionLocal() as db:
        # 1. Risk
        inv = db.query(Inventory).filter(Inventory.sku_id == sku_id, Inventory.store_id == source_store_id).first()
        if not inv:
            return {"error": "Inventory not found"}
        risk = calculate_inventory_risk(inv).model_dump()
        logger.info(f"risk_completed: level={risk.get('risk_level')}")
        
        # 2. Demand
        destinations_model = find_destination_candidates(db, sku_id, source_store_id)
        destinations = destinations_model.model_dump() if destinations_model else {}
        logger.info(f"demand_completed: found {len(destinations.get('destinations', []))} destinations")
        
        # 3. Decision
        decision_model = evaluate_decision(db, sku_id, source_store_id)
        decision = decision_model.model_dump() if decision_model else {}
        logger.info(f"decision_completed: action={decision.get('selected_action')}")
        
        # 4. Logistics
        logistics_model = get_integrated_recommendation(db, sku_id, source_store_id)
        logistics = logistics_model.model_dump() if logistics_model else {}
        logger.info(f"logistics_completed")
        
        return {
            "sku_id": sku_id,
            "source_store_id": source_store_id,
            "risk": risk,
            "destination_matches": destinations,
            "decision": decision,
            "logistics": logistics
        }

def run_complete_recovery_workflow(
    sku_id: str,
    source_store_id: str,
    actual_units_sold: int,
    actual_recovered_value: float,
    actual_logistics_cost: float,
    actual_handling_cost: float
) -> Dict[str, Any]:
    """
    MUTATES STATE.
    Executes the full operational lifecycle.
    """
    logger.info(f"workflow_started: execution for {sku_id} at {source_store_id}")
    
    # 1. Analyze
    analysis = run_recovery_analysis(sku_id, source_store_id)
    
    decision = analysis.get("decision")
    if not decision:
        return {
            "workflow_status": "FAILED",
            "failed_stage": "ANALYSIS",
            "message": analysis.get("error", "Unknown error during analysis.")
        }
        
    selected_action = decision.get("selected_action")
    if selected_action != RecoveryActionType.TRANSFER and selected_action != RecoveryActionType.TRANSFER.value:
        logger.info("workflow_completed: decision is not TRANSFER, skipping execution.")
        return {
            "workflow_status": "COMPLETED",
            "analysis": analysis,
            "message": f"Action was {selected_action}, no transfer required."
        }
    
    logistics = analysis["logistics"]
    if not logistics.get("logistics") or not logistics.get("logistics").get("selected_partner"):
        return {
            "workflow_status": "FAILED",
            "failed_stage": "LOGISTICS",
            "message": "No eligible logistics partner available before expiry."
        }
        
    destination_store_id = analysis["decision"]["selected_destination_store_id"]
    quantity = analysis["decision"]["recommended_quantity"]
    partner_id = logistics["logistics"]["selected_partner"]["partner_id"]
    
    if not destination_store_id:
        return {
            "workflow_status": "FAILED",
            "failed_stage": "DECISION",
            "message": "No eligible destination."
        }

    transfer = None
    outcome = None
    history_indexed = False
    
    try:
        with SessionLocal() as db:
            # Idempotency check
            from ..models.transfer import TransferOrder
            existing = db.query(TransferOrder).filter(
                TransferOrder.sku_id == sku_id,
                TransferOrder.source_store_id == source_store_id,
                TransferOrder.destination_store_id == destination_store_id,
                TransferOrder.status.in_([TransferStatus.CREATED, TransferStatus.APPROVED, TransferStatus.ASSIGNED, TransferStatus.PICKUP_PENDING, TransferStatus.IN_TRANSIT, TransferStatus.DELIVERED, TransferStatus.COMPLETED])
            ).first()
            if existing:
                transfer = existing
                logger.info(f"Found existing transfer: {transfer.transfer_id}")
            else:
                transfer = create_transfer_from_recommendation(db, sku_id, source_store_id)
                logger.info(f"transfer_created: {transfer.transfer_id}")
                
            transfer_id = transfer.transfer_id
            
            # State Machine Progression
            if transfer.status == TransferStatus.CREATED:
                transfer = approve_transfer(db, transfer_id)
                logger.info("transfer_approved")
            if transfer.status == TransferStatus.APPROVED:
                transfer = assign_transfer(db, transfer_id)
                logger.info("transfer_assigned")
            if transfer.status == TransferStatus.ASSIGNED:
                transfer = mark_pickup_pending(db, transfer_id)
                logger.info("pickup_started")
            if transfer.status == TransferStatus.PICKUP_PENDING:
                transfer = start_transfer(db, transfer_id)
                logger.info("transit_started")
            if transfer.status == TransferStatus.IN_TRANSIT:
                transfer = mark_delivered(db, transfer_id)
                logger.info("transfer_delivered")
            if transfer.status == TransferStatus.DELIVERED:
                transfer = complete_transfer(db, transfer_id)
                logger.info("transfer_completed")

            # Outcome Engine
            from ..models.outcome import Outcome
            existing_outcome = db.query(Outcome).filter(Outcome.transfer_id == transfer_id).first()
            if existing_outcome:
                outcome = existing_outcome
                logger.info(f"Found existing outcome: {outcome.outcome_id}")
            elif transfer.status == TransferStatus.COMPLETED:
                outcome = create_outcome_from_transfer(db, transfer_id)
                logger.info("outcome_created")
                
            if outcome and outcome.outcome_status == OutcomeStatus.PENDING:
                outcome_id = outcome.outcome_id
                record_actual_sales(db, outcome_id, actual_units_sold)
                record_actual_financials(db, outcome_id, actual_recovered_value, actual_logistics_cost, actual_handling_cost)
                outcome = finalize_outcome(db, outcome_id)
                logger.info("outcome_finalized")

    except Exception as e:
        logger.error(f"Workflow failed at execution stage: {str(e)}")
        return {
            "workflow_status": "FAILED",
            "failed_stage": "EXECUTION",
            "message": str(e),
            "transfer": {"transfer_id": transfer.transfer_id, "status": transfer.status.value} if transfer else None
        }

    # Historical Indexing (Out of primary transaction to prevent business rollback on OpenSearch failure)
    if outcome and outcome.outcome_status == OutcomeStatus.FINALIZED:
        try:
            with SessionLocal() as db:
                refreshed_transfer = db.query(TransferOrder).filter(TransferOrder.transfer_id == transfer_id).first()
                from ..models.outcome import Outcome
                refreshed_outcome = db.query(Outcome).filter(Outcome.outcome_id == outcome.outcome_id).first()
                history_indexed = upsert_outcome_history(refreshed_outcome, refreshed_transfer)
                if history_indexed:
                    logger.info("history_indexed")
        except Exception as e:
            logger.warning(f"Failed to index history: {str(e)}")
            history_indexed = False
            
    logger.info("workflow_completed")
    
    return {
        "workflow_status": "COMPLETED",
        "analysis": analysis,
        "transfer": {
            "transfer_id": transfer.transfer_id,
            "status": transfer.status.value
        } if transfer else None,
        "outcome": {
            "outcome_id": outcome.outcome_id,
            "status": outcome.outcome_status.value
        } if outcome else None,
        "history": {
            "indexed": history_indexed
        }
    }

def get_workflow_status(transfer_id: str) -> Dict[str, Any]:
    with SessionLocal() as db:
        t = get_transfer(db, transfer_id)
        o = None
        try:
            from ..models.outcome import Outcome
            o = db.query(Outcome).filter(Outcome.transfer_id == transfer_id).first()
        except Exception:
            pass
            
        history = None
        try:
            from ..opensearch.repository import get_history_by_transfer_id
            history = get_history_by_transfer_id(transfer_id)
        except Exception:
            pass
            
        return {
            "transfer": {
                "transfer_id": t.transfer_id,
                "status": t.status.value
            },
            "outcome": {
                "outcome_id": o.outcome_id,
                "status": o.outcome_status.value
            } if o else None,
            "history_indexed": bool(history)
        }
