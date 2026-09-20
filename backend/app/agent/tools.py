from typing import Dict, Any, List
from strands import tool
from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..database import SessionLocal
from ..services.risk_engine import calculate_inventory_risk
from ..services.demand_engine import find_destination_candidates
from ..services.decision_engine import evaluate_decision
from ..services.logistics_engine import get_integrated_recommendation
from ..services.transfer_engine import get_transfer, get_transfer_summary
from ..services.outcome_engine import get_outcome, list_outcomes, get_outcome_summary
from ..opensearch.repository import search_history
from ..models.inventory import Inventory

@tool
def get_inventory_risk(sku_id: str, store_id: str) -> Dict[str, Any]:
    """
    Get the inventory risk profile for a specific SKU at a specific store.
    Returns calculated values for days to expiry, daily sales, expected sales before expiry,
    at-risk quantity, at-risk value, risk percentage, risk score, and risk level (e.g. CRITICAL, HIGH, MODERATE, LOW).
    If no inventory matches, it returns an error dictionary.
    """
    with SessionLocal() as db:
        inv = db.query(Inventory).filter(Inventory.sku_id == sku_id, Inventory.store_id == store_id).first()
        if not inv:
            return {"error": f"No inventory found for SKU {sku_id} at {store_id}"}
            
        risk = calculate_inventory_risk(inv)
        return {
            "sku_id": risk.sku_id,
            "product_name": inv.product_name,
            "store_id": risk.store_id,
            "quantity": risk.quantity,
            "days_to_expiry": risk.days_to_expiry,
            "daily_sales": risk.daily_sales_7d,
            "expected_sales_before_expiry": risk.expected_sales_before_expiry,
            "expected_remaining_quantity": risk.expected_remaining_quantity,
            "at_risk_quantity": risk.at_risk_quantity,
            "at_risk_value": risk.at_risk_value,
            "risk_percentage": risk.risk_percentage,
            "risk_score": risk.risk_score,
            "risk_level": risk.risk_level
        }

@tool
def find_destination_matches(sku_id: str, source_store_id: str) -> Dict[str, Any]:
    """
    Find nearby stores that have demand for the given SKU to absorb at-risk inventory.
    Returns ranked destinations, their capacity, suitability score, and recommended transfer quantity.
    """
    with SessionLocal() as db:
        try:
            match_res = find_destination_candidates(db, sku_id, source_store_id)
            return {
                "source_store": match_res.source_store_id,
                "source_at_risk_quantity": match_res.source_risk.at_risk_quantity if match_res.source_risk else 0,
                "destinations": [
                    {
                        "store_id": d.destination_store_id,
                        "distance_km": d.distance_km,
                        "capacity": d.usable_destination_capacity,
                        "suitability_score": d.destination_suitability_score,
                        "recommended_transfer_quantity": d.recommended_transfer_quantity,
                        "explanation": d.explanation
                    } for d in match_res.candidates
                ]
            }
        except HTTPException as e:
            return {"error": e.detail}

@tool
def evaluate_recovery_options(sku_id: str, store_id: str) -> Dict[str, Any]:
    """
    Evaluate all economic recovery options (TRANSFER, DISCOUNT, BUNDLE, PROMOTE, RETURN, DISPOSE).
    Returns the expected net recovery of each and the selected action.
    """
    with SessionLocal() as db:
        try:
            decision = evaluate_decision(db, sku_id, store_id)
            return {
                "selected_action": decision.selected_action.value,
                "selected_destination_store_id": decision.selected_destination_store_id,
                "recommended_quantity": decision.recommended_quantity,
                "expected_net_recovery": decision.expected_net_recovery,
                "decision_reason": decision.decision_reason,
                "actions": [
                    {
                        "action": a.action.value,
                        "expected_net_recovery": a.expected_net_recovery,
                        "economically_viable": a.economically_viable,
                        "reason": a.reason
                    } for a in decision.actions
                ]
            }
        except HTTPException as e:
            return {"error": e.detail}

@tool
def optimize_logistics(sku_id: str, source_store_id: str) -> Dict[str, Any]:
    """
    Get the logistics optimization for a transfer, showing the selected logistics partner, 
    distance, delivery cost, and ETA.
    """
    with SessionLocal() as db:
        try:
            rec = get_integrated_recommendation(db, sku_id, source_store_id)
            if not rec.logistics:
                return {"error": "Logistics evaluation not available or not applicable."}
            return {
                "destination_store_id": rec.decision.selected_destination_store_id,
                "transfer_quantity": rec.decision.recommended_quantity,
                "selected_partner": rec.logistics.selected_partner.partner_name,
                "distance_km": rec.logistics.selected_partner.distance_km,
                "estimated_delivery_cost": rec.logistics.delivery_cost,
                "estimated_eta_minutes": rec.logistics.eta_minutes,
                "logistics_suitability_score": rec.logistics.selected_partner.logistics_suitability_score if rec.logistics.selected_partner else 0,
                "logistics_adjusted_net_recovery": rec.logistics_adjusted_net_recovery,
                "transfer_viable": rec.transfer_still_viable,
                "reason": rec.reason
            }
        except HTTPException as e:
            return {"error": e.detail}

@tool
def get_transfer_status(transfer_id: str) -> Dict[str, Any]:
    """
    Get the current operational status of a transfer by its ID.
    """
    with SessionLocal() as db:
        try:
            order = get_transfer(db, transfer_id)
            return {
                "transfer_id": order.transfer_id,
                "status": order.status.value,
                "sku_id": order.sku_id,
                "source_store": order.source_store_id,
                "destination_store": order.destination_store_id,
                "quantity": order.quantity,
                "logistics_partner": order.logistics_partner_name,
                "estimated_delivery_cost": order.estimated_delivery_cost,
                "estimated_eta_minutes": order.estimated_eta_minutes,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "completed_at": order.completed_at.isoformat() if order.completed_at else None,
            }
        except HTTPException as e:
            return {"error": e.detail}

@tool
def get_transfer_outcome(transfer_id: str) -> Dict[str, Any]:
    """
    Get the final outcome and predicted vs actual results of a completed transfer.
    """
    with SessionLocal() as db:
        try:
            outcomes = list_outcomes(db, transfer_id=transfer_id)
            if not outcomes:
                return {"error": f"No outcome found for transfer {transfer_id}"}
            outcome = outcomes[0]
            return {
                "outcome_id": outcome.outcome_id,
                "outcome_status": outcome.outcome_status.value,
                "predicted_units_sold": outcome.predicted_units_sold,
                "actual_units_sold": outcome.actual_units_sold,
                "predicted_net_recovery": outcome.predicted_net_recovery,
                "actual_net_recovery": outcome.actual_net_recovery,
                "recovery_variance": outcome.recovery_variance,
                "recovery_percentage": outcome.recovery_percentage,
                "sell_through_rate": outcome.sell_through_rate,
                "logistics_cost_variance": outcome.logistics_cost_variance,
                "recovery_accuracy_percentage": outcome.recovery_accuracy_percentage
            }
        except HTTPException as e:
            return {"error": e.detail}

@tool
def get_network_summary() -> Dict[str, Any]:
    """
    Get the high-level network summary containing transfer counts and total recovery metrics.
    """
    with SessionLocal() as db:
        trans_sum = get_transfer_summary(db)
        out_sum = get_outcome_summary(db)
        return {
            "transfers": trans_sum,
            "outcomes": out_sum
        }

@tool
def search_historical_recovery(query: str, sku_id: str = None, store_id: str = None, action: str = None, partner_id: str = None) -> Dict[str, Any]:
    """
    Search the OpenSearch historical intelligence layer for past transfers and outcomes.
    Useful for answering questions about what happened in previous transfers, average recoveries, and accuracy.
    """
    
    # We map store_id to both source and destination depending on context,
    # but the simplest general search passes it to source_store_id for now
    res = search_history(
        q=query if query else None,
        sku_id=sku_id if sku_id else None,
        source_store_id=store_id if store_id else None,
        action=action if action else None,
        partner_id=partner_id if partner_id else None,
        limit=10
    )
    return res
