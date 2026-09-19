from pydantic import BaseModel
from typing import List, Optional
from .risk import RiskItem

class DemandCandidate(BaseModel):
    source_store_id: str
    destination_store_id: str
    sku_id: str
    product_name: str
    distance_km: float
    source_at_risk_quantity: int
    destination_current_stock: int
    destination_daily_demand: float
    days_remaining: int
    expected_future_demand: float
    usable_destination_capacity: float
    recommended_transfer_quantity: int
    demand_score: float
    capacity_score: float
    distance_score: float
    destination_suitability_score: float
    cold_chain_compatible: bool
    eligible: bool
    explanation: str

class DemandMatchResponse(BaseModel):
    sku_id: str
    source_store_id: str
    source_risk: Optional[RiskItem] = None
    candidates: List[DemandCandidate]

class BestMatchResponse(BaseModel):
    sku_id: str
    source_store_id: str
    matched: bool
    destination: Optional[DemandCandidate] = None
    reason: Optional[str] = None

class DemandSummaryResponse(BaseModel):
    at_risk_skus: int
    source_stores_with_risk: int
    eligible_destination_stores: int
    total_candidate_matches: int
    total_transferable_units: int
    unmatched_at_risk_units: int
