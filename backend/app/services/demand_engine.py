import math
from typing import List, Optional
from sqlalchemy.orm import Session
from ..models.inventory import Inventory
from ..models.store import Store
from ..schemas.demand import DemandCandidate, DemandMatchResponse, BestMatchResponse, DemandSummaryResponse
from .risk_engine import calculate_inventory_risk

# Configuration
TARGET_FILL_RATIO = 0.80
MAX_TRANSFER_DISTANCE_KM = 15.0
EARTH_RADIUS_KM = 6371.0

def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on the earth."""
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    distance = EARTH_RADIUS_KM * c
    return round(distance, 2)

def calculate_destination_capacity(current_stock: int, daily_demand: float, remaining_days: int) -> float:
    """Calculate how many additional units a store can absorb before expiry."""
    expected_future_demand = daily_demand * remaining_days
    destination_capacity = max(expected_future_demand - current_stock, 0)
    return destination_capacity

def check_cold_chain(temperature_class: str, destination_store: Store) -> bool:
    """Check if the destination store is compatible with the product's temperature class."""
    if temperature_class and ("c" in temperature_class.lower() or "cold" in temperature_class.lower() or "-" in temperature_class):
        return destination_store.supports_cold_chain
    return True # Ambient products can go anywhere

def calculate_candidate_score(demand: float, capacity: float, distance: float) -> float:
    """Calculate a deterministic 0-100 score for destination suitability."""
    # Normalized components (simple heuristics for MVP)
    # Demand score: caps out at 20 units/day for normalization
    demand_strength_score = min((demand / 20.0) * 100, 100.0)
    
    # Capacity score: caps out at 100 units for normalization
    capacity_score = min((capacity / 100.0) * 100, 100.0)
    
    # Distance score: higher for shorter distances
    if distance > MAX_TRANSFER_DISTANCE_KM:
        distance_score = 0.0
    else:
        # Scale 0-15km to 100-0 score
        distance_score = max(((MAX_TRANSFER_DISTANCE_KM - distance) / MAX_TRANSFER_DISTANCE_KM) * 100, 0.0)

    # Weighted combination
    overall_score = (0.50 * demand_strength_score) + (0.35 * capacity_score) + (0.15 * distance_score)
    return round(overall_score, 2)

def generate_explanation(store_name: str, demand: float, capacity: int, distance: float, cold_chain: bool) -> str:
    cc_text = "supports the required cold chain" if cold_chain else "is ambient-only"
    return f"{store_name} has demand of {demand} units/day, can absorb {capacity} units before expiry, is {distance} km away, and {cc_text}."

def find_destination_candidates(db: Session, sku_id: str, source_store_id: str, minimum_risk_level: str = "HIGH") -> DemandMatchResponse:
    # 1. Fetch Source Inventory
    source_inv = db.query(Inventory).filter(Inventory.sku_id == sku_id, Inventory.store_id == source_store_id).first()
    if not source_inv:
        return DemandMatchResponse(sku_id=sku_id, source_store_id=source_store_id, source_risk=None, candidates=[])
        
    source_store = db.query(Store).filter(Store.store_id == source_store_id).first()
    
    # 2. Check Risk Level
    source_risk = calculate_inventory_risk(source_inv)
    risk_hierarchy = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    if risk_hierarchy.get(source_risk.risk_level, 0) < risk_hierarchy.get(minimum_risk_level, 3):
        return DemandMatchResponse(sku_id=sku_id, source_store_id=source_store_id, source_risk=source_risk, candidates=[])

    if source_risk.at_risk_quantity <= 0:
        return DemandMatchResponse(sku_id=sku_id, source_store_id=source_store_id, source_risk=source_risk, candidates=[])

    # 3. Fetch Destination Candidates
    # Get all inventory records for the same SKU at different stores
    dest_inventories = db.query(Inventory).filter(Inventory.sku_id == sku_id, Inventory.store_id != source_store_id).all()
    
    candidates = []
    
    for dest_inv in dest_inventories:
        dest_store = db.query(Store).filter(Store.store_id == dest_inv.store_id).first()
        
        # Calculate Distance
        distance = calculate_distance_km(
            source_store.latitude, source_store.longitude, 
            dest_store.latitude, dest_store.longitude
        )
        
        if distance > MAX_TRANSFER_DISTANCE_KM:
            continue # Exclude stores that are too far
            
        # Capacity
        daily_demand = dest_inv.daily_sales_7d
        if daily_demand <= 0:
            continue # Exclude zero-demand stores
            
        days_remaining = source_risk.days_to_expiry
        destination_capacity = calculate_destination_capacity(dest_inv.quantity, daily_demand, days_remaining)
        usable_destination_capacity = destination_capacity * TARGET_FILL_RATIO
        
        # Recommended transfer quantity
        recommended_transfer_quantity = int(min(source_risk.at_risk_quantity, usable_destination_capacity))
        
        if recommended_transfer_quantity <= 0:
            continue
            
        # Cold Chain
        cold_chain_compatible = check_cold_chain(source_inv.temperature_class, dest_store)
        if not cold_chain_compatible:
            continue
            
        # Score
        demand_score = min((daily_demand / 20.0) * 100, 100.0)
        capacity_score = min((usable_destination_capacity / 100.0) * 100, 100.0)
        distance_score = max(((MAX_TRANSFER_DISTANCE_KM - distance) / MAX_TRANSFER_DISTANCE_KM) * 100, 0.0)
        
        suitability_score = calculate_candidate_score(daily_demand, usable_destination_capacity, distance)
        
        # Explanation
        explanation = generate_explanation(dest_store.store_name, daily_demand, int(usable_destination_capacity), distance, cold_chain_compatible)
        
        candidate = DemandCandidate(
            source_store_id=source_store_id,
            destination_store_id=dest_inv.store_id,
            sku_id=sku_id,
            product_name=dest_inv.product_name,
            distance_km=distance,
            source_at_risk_quantity=source_risk.at_risk_quantity,
            destination_current_stock=dest_inv.quantity,
            destination_daily_demand=daily_demand,
            days_remaining=days_remaining,
            expected_future_demand=daily_demand * days_remaining,
            usable_destination_capacity=usable_destination_capacity,
            recommended_transfer_quantity=recommended_transfer_quantity,
            demand_score=round(demand_score, 2),
            capacity_score=round(capacity_score, 2),
            distance_score=round(distance_score, 2),
            destination_suitability_score=suitability_score,
            cold_chain_compatible=cold_chain_compatible,
            eligible=True,
            explanation=explanation
        )
        candidates.append(candidate)
        
    # Rank candidates
    candidates.sort(key=lambda x: x.destination_suitability_score, reverse=True)
    
    return DemandMatchResponse(
        sku_id=sku_id,
        source_store_id=source_store_id,
        source_risk=source_risk,
        candidates=candidates
    )

def get_best_match(db: Session, sku_id: str, source_store_id: str) -> BestMatchResponse:
    match_response = find_destination_candidates(db, sku_id, source_store_id)
    
    if not match_response.source_risk:
        return BestMatchResponse(sku_id=sku_id, source_store_id=source_store_id, matched=False, reason="SKU not found or no risk data.")
        
    if not match_response.candidates:
        return BestMatchResponse(sku_id=sku_id, source_store_id=source_store_id, matched=False, reason="No eligible destination store found")
        
    return BestMatchResponse(
        sku_id=sku_id,
        source_store_id=source_store_id,
        matched=True,
        destination=match_response.candidates[0]
    )

def get_demand_summary(db: Session) -> DemandSummaryResponse:
    all_inv = db.query(Inventory).all()
    
    at_risk_skus = 0
    source_stores = set()
    total_transferable_units = 0
    total_unmatched_units = 0
    
    # Track destination eligibility logic globally
    total_candidate_matches = 0
    eligible_destinations = set()
    
    for inv in all_inv:
        risk = calculate_inventory_risk(inv)
        if risk.risk_level in ["HIGH", "CRITICAL"] and risk.at_risk_quantity > 0:
            at_risk_skus += 1
            source_stores.add(inv.store_id)
            
            # Find matches for this specific risk block
            matches = find_destination_candidates(db, inv.sku_id, inv.store_id)
            if matches.candidates:
                best = matches.candidates[0]
                total_candidate_matches += len(matches.candidates)
                for c in matches.candidates:
                    eligible_destinations.add(c.destination_store_id)
                    
                total_transferable_units += best.recommended_transfer_quantity
                total_unmatched_units += (risk.at_risk_quantity - best.recommended_transfer_quantity)
            else:
                total_unmatched_units += risk.at_risk_quantity
                
    return DemandSummaryResponse(
        at_risk_skus=at_risk_skus,
        source_stores_with_risk=len(source_stores),
        eligible_destination_stores=len(eligible_destinations),
        total_candidate_matches=total_candidate_matches,
        total_transferable_units=total_transferable_units,
        unmatched_at_risk_units=total_unmatched_units
    )
