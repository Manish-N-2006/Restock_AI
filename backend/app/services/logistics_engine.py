from sqlalchemy.orm import Session
from typing import List, Optional
import math

from ..models.inventory import Inventory
from ..models.store import Store
from ..models.logistics import LogisticsPartner
from ..schemas.decision import RecoveryActionType
from ..schemas.logistics import (
    LogisticsPartnerEvaluation,
    BestLogisticsResponse,
    LogisticsOptionsResponse,
    IntegratedRecommendationResponse,
    LogisticsIntegrationResult,
    LogisticsSummaryResponse
)
from .risk_engine import calculate_inventory_risk
from .demand_engine import calculate_distance_km
from .decision_engine import evaluate_decision

EXPIRY_SAFETY_BUFFER_MINUTES = 60
COST_WEIGHT = 0.50
ETA_WEIGHT = 0.35
CAPACITY_WEIGHT = 0.15
TRANSFER_HANDLING_COST = 10.0 # From decision_engine.py (hardcoded reuse since it's an assumption)

def evaluate_logistics_options(
    db: Session, 
    sku_id: str, 
    source_store_id: str, 
    destination_store_id: str, 
    transfer_quantity: int
) -> LogisticsOptionsResponse:
    
    # Input validation & data fetching
    source_store = db.query(Store).filter(Store.store_id == source_store_id).first()
    dest_store = db.query(Store).filter(Store.store_id == destination_store_id).first()
    inv = db.query(Inventory).filter(Inventory.sku_id == sku_id, Inventory.store_id == source_store_id).first()
    
    if not source_store or not dest_store or not inv or transfer_quantity <= 0:
        return LogisticsOptionsResponse(
            sku_id=sku_id,
            source_store_id=source_store_id,
            destination_store_id=destination_store_id,
            transfer_quantity=transfer_quantity,
            matched=False,
            options=[]
        )
        
    risk = calculate_inventory_risk(inv)
    remaining_minutes = risk.days_to_expiry * 24 * 60
    cold_chain_required = False
    
    if inv.temperature_class and ("c" in inv.temperature_class.lower() or "cold" in inv.temperature_class.lower() or "-" in inv.temperature_class):
        cold_chain_required = True
        
    distance = calculate_distance_km(
        source_store.latitude, source_store.longitude, 
        dest_store.latitude, dest_store.longitude
    )
    
    partners = db.query(LogisticsPartner).all()
    evaluations = []
    
    # First pass: Evaluate hard constraints and raw values
    eligible_partners = []
    for lp in partners:
        reason = ""
        eligible = True
        
        # 1. Capacity
        if lp.capacity_units < transfer_quantity:
            eligible = False
            reason = "Insufficient transport capacity"
            
        # 2. Cold Chain
        elif cold_chain_required and not lp.supports_cold_chain:
            eligible = False
            reason = "Partner does not support the required cold chain"
            
        # 3. Expiry ETA
        elif remaining_minutes <= 0:
            eligible = False
            reason = "Product already expired"
        elif (lp.average_eta_minutes + EXPIRY_SAFETY_BUFFER_MINUTES) > remaining_minutes:
            eligible = False
            reason = "ETA exceeds expiry window"
            
        capacity_headroom = max(lp.capacity_units - transfer_quantity, 0) if eligible else (lp.capacity_units - transfer_quantity)
        estimated_delivery_cost = lp.base_cost + (distance * lp.cost_per_km)
        
        if eligible:
            reason = "Eligible partner with suitable capacity, cold-chain support, competitive delivery cost, and ETA before expiry."
            
        eval_dict = {
            "partner_id": lp.partner_id,
            "partner_name": lp.partner_name,
            "distance_km": distance,
            "transfer_quantity": transfer_quantity,
            "capacity_units": lp.capacity_units,
            "capacity_headroom": capacity_headroom,
            "estimated_delivery_cost": estimated_delivery_cost,
            "average_eta_minutes": lp.average_eta_minutes,
            "cold_chain_required": cold_chain_required,
            "supports_cold_chain": lp.supports_cold_chain,
            "eligible": eligible,
            "reason": reason
        }
        evaluations.append(eval_dict)
        
        if eligible:
            eligible_partners.append(eval_dict)
            
    # Normalization phase (only for eligible partners)
    if eligible_partners:
        min_cost = min(p["estimated_delivery_cost"] for p in eligible_partners)
        max_cost = max(p["estimated_delivery_cost"] for p in eligible_partners)
        
        min_eta = min(p["average_eta_minutes"] for p in eligible_partners)
        max_eta = max(p["average_eta_minutes"] for p in eligible_partners)
        
        min_cap = min(p["capacity_headroom"] for p in eligible_partners)
        max_cap = max(p["capacity_headroom"] for p in eligible_partners)
        
        # We need the final evaluations mapped by partner_id for the final list
        for p in eligible_partners:
            # Cost Score: lower cost = higher score (inverse)
            if max_cost == min_cost:
                p["cost_score"] = 100.0
            else:
                p["cost_score"] = 100.0 * (1.0 - ((p["estimated_delivery_cost"] - min_cost) / (max_cost - min_cost)))
                
            # ETA Score: lower ETA = higher score (inverse)
            if max_eta == min_eta:
                p["eta_score"] = 100.0
            else:
                p["eta_score"] = 100.0 * (1.0 - ((p["average_eta_minutes"] - min_eta) / (max_eta - min_eta)))
                
            # Capacity Score: higher headroom = higher score
            if max_cap == min_cap:
                p["capacity_score"] = 100.0
            else:
                p["capacity_score"] = 100.0 * ((p["capacity_headroom"] - min_cap) / (max_cap - min_cap))
                
            p["logistics_suitability_score"] = (
                (COST_WEIGHT * p["cost_score"]) +
                (ETA_WEIGHT * p["eta_score"]) +
                (CAPACITY_WEIGHT * p["capacity_score"])
            )
            
    # Assemble final objects
    final_results = []
    for e in evaluations:
        if not e["eligible"]:
            e["cost_score"] = 0.0
            e["eta_score"] = 0.0
            e["capacity_score"] = 0.0
            e["logistics_suitability_score"] = 0.0
            
        final_results.append(LogisticsPartnerEvaluation(
            partner_id=e["partner_id"],
            partner_name=e["partner_name"],
            distance_km=e["distance_km"],
            transfer_quantity=e["transfer_quantity"],
            capacity_units=e["capacity_units"],
            capacity_headroom=e["capacity_headroom"],
            estimated_delivery_cost=round(e["estimated_delivery_cost"], 2),
            average_eta_minutes=e["average_eta_minutes"],
            cold_chain_required=e["cold_chain_required"],
            supports_cold_chain=e["supports_cold_chain"],
            cost_score=round(e["cost_score"], 2),
            eta_score=round(e["eta_score"], 2),
            capacity_score=round(e["capacity_score"], 2),
            logistics_suitability_score=round(e["logistics_suitability_score"], 2),
            eligible=e["eligible"],
            reason=e["reason"]
        ))
        
    # Sort eligible first, then by suitability descending, then cost ascending, ETA ascending, capacity descending, ID
    final_results.sort(key=lambda x: (
        x.eligible,
        x.logistics_suitability_score,
        -x.estimated_delivery_cost,
        -x.average_eta_minutes,
        x.capacity_headroom,
        # Inverse partner_id sort string so it works in lambda cleanly
        x.partner_id
    ), reverse=True)
    
    # Because of string negative sorting limitation in python lambda mixed types, 
    # we sort specifically by eligible & suitability descending, and handle ties with a custom cmp if needed.
    # Actually tuple sorting with negative floats works fine. But string needs to just be at end, reverse=True means descending.
    # Let's fix the sort to be perfectly correct:
    final_results.sort(
        key=lambda x: (
            -1 if x.eligible else 0, # Eligible first (lowest number when ascending, wait reverse=False)
            -x.logistics_suitability_score,
            x.estimated_delivery_cost,
            x.average_eta_minutes,
            -x.capacity_headroom,
            x.partner_id
        )
    )
    
    return LogisticsOptionsResponse(
        sku_id=sku_id,
        source_store_id=source_store_id,
        destination_store_id=destination_store_id,
        transfer_quantity=transfer_quantity,
        matched=len(eligible_partners) > 0,
        options=final_results
    )

def get_best_logistics_partner(
    db: Session, 
    sku_id: str, 
    source_store_id: str, 
    destination_store_id: str, 
    transfer_quantity: int
) -> BestLogisticsResponse:
    
    options_res = evaluate_logistics_options(db, sku_id, source_store_id, destination_store_id, transfer_quantity)
    
    if not options_res.matched:
        reason = "No eligible logistics partner can complete the transfer before expiry."
        if options_res.options:
            reason = options_res.options[0].reason # Give reason of highest ranked but ineligible partner
        return BestLogisticsResponse(
            matched=False,
            sku_id=sku_id,
            source_store_id=source_store_id,
            destination_store_id=destination_store_id,
            transfer_quantity=transfer_quantity,
            distance_km=0.0,
            selected_partner=None,
            reason=reason
        )
        
    best = options_res.options[0]
    return BestLogisticsResponse(
        matched=True,
        sku_id=sku_id,
        source_store_id=source_store_id,
        destination_store_id=destination_store_id,
        transfer_quantity=transfer_quantity,
        distance_km=best.distance_km,
        selected_partner=best,
        reason=None
    )

def get_integrated_recommendation(db: Session, sku_id: str, source_store_id: str) -> IntegratedRecommendationResponse:
    # 1. Run Decision Engine
    decision = evaluate_decision(db, sku_id, source_store_id)
    inv = db.query(Inventory).filter(Inventory.sku_id == sku_id, Inventory.store_id == source_store_id).first()
    
    # If not a transfer, logistics is not needed
    if decision.selected_action != RecoveryActionType.TRANSFER:
        return IntegratedRecommendationResponse(
            decision=decision,
            logistics=None,
            logistics_adjusted_net_recovery=decision.expected_net_recovery,
            transfer_still_viable=decision.expected_net_recovery > 0,
            reason=f"Action is {decision.selected_action.value}, logistics optimization bypassed."
        )
        
    dest_store_id = decision.selected_destination_store_id
    qty = decision.recommended_quantity
    
    # 2. Run Logistics Engine
    best_logistics = get_best_logistics_partner(db, sku_id, source_store_id, dest_store_id, qty)
    
    if not best_logistics.matched:
        return IntegratedRecommendationResponse(
            decision=decision,
            logistics=None,
            logistics_adjusted_net_recovery=0.0,
            transfer_still_viable=False,
            reason=f"Logistics failed: {best_logistics.reason}"
        )
        
    # 3. Recalculate Economics
    actual_logistics_cost = best_logistics.selected_partner.estimated_delivery_cost
    expected_recovered_value = qty * inv.selling_price
    handling_cost = qty * TRANSFER_HANDLING_COST
    
    logistics_adjusted_net_recovery = round(expected_recovered_value - actual_logistics_cost - handling_cost, 2)
    transfer_still_viable = logistics_adjusted_net_recovery > 0
    
    reason = "Transfer remains economically viable with optimal logistics." if transfer_still_viable else "The selected logistics cost reduces expected net recovery below the viability threshold."
    
    return IntegratedRecommendationResponse(
        decision=decision,
        logistics=LogisticsIntegrationResult(
            selected_partner=best_logistics.selected_partner,
            delivery_cost=best_logistics.selected_partner.estimated_delivery_cost,
            eta_minutes=best_logistics.selected_partner.average_eta_minutes
        ),
        logistics_adjusted_net_recovery=logistics_adjusted_net_recovery,
        transfer_still_viable=transfer_still_viable,
        reason=reason
    )

def get_logistics_summary(db: Session) -> LogisticsSummaryResponse:
    # Get all high-risk decisions and see which are transfers
    all_inv = db.query(Inventory).all()
    transfers = []
    
    for inv in all_inv:
        risk = calculate_inventory_risk(inv)
        if risk.risk_level in ["HIGH", "CRITICAL"] and risk.at_risk_quantity > 0:
            dec = evaluate_decision(db, inv.sku_id, inv.store_id)
            if dec.selected_action == RecoveryActionType.TRANSFER:
                transfers.append(dec)
                
    partners = db.query(LogisticsPartner).all()
    
    total_evals = 0
    eligible_evals = 0
    rejected_evals = 0
    transfers_viable = 0
    transfers_not_viable = 0
    total_cost = 0.0
    total_eta = 0
    cost_count = 0
    
    for t in transfers:
        best = get_best_logistics_partner(db, t.sku_id, t.store_id, t.selected_destination_store_id, t.recommended_quantity)
        
        # Get options to count evaluations
        opts = evaluate_logistics_options(db, t.sku_id, t.store_id, t.selected_destination_store_id, t.recommended_quantity)
        for o in opts.options:
            total_evals += 1
            if o.eligible:
                eligible_evals += 1
            else:
                rejected_evals += 1
                
        if best.matched:
            transfers_viable += 1
            total_cost += best.selected_partner.estimated_delivery_cost
            total_eta += best.selected_partner.average_eta_minutes
            cost_count += 1
        else:
            transfers_not_viable += 1
            
    avg_cost = total_cost / cost_count if cost_count > 0 else 0.0
    avg_eta = total_eta / cost_count if cost_count > 0 else 0.0
    
    cold_chain_count = sum(1 for p in partners if p.supports_cold_chain)
    
    return LogisticsSummaryResponse(
        total_logistics_partners=len(partners),
        eligible_partner_evaluations=eligible_evals,
        rejected_partner_evaluations=rejected_evals,
        transfers_with_viable_partner=transfers_viable,
        transfers_with_no_viable_partner=transfers_not_viable,
        average_estimated_delivery_cost=round(avg_cost, 2),
        average_eta=round(avg_eta, 2),
        cold_chain_compatible_partners=cold_chain_count
    )
