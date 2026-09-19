from pydantic import BaseModel
from typing import List, Optional
from .decision import DecisionResponse

class LogisticsPartnerEvaluation(BaseModel):
    partner_id: str
    partner_name: str
    distance_km: float
    transfer_quantity: int
    capacity_units: int
    capacity_headroom: int
    estimated_delivery_cost: float
    average_eta_minutes: int
    cold_chain_required: bool
    supports_cold_chain: bool
    cost_score: float
    eta_score: float
    capacity_score: float
    logistics_suitability_score: float
    eligible: bool
    reason: str

class BestLogisticsResponse(BaseModel):
    matched: bool
    sku_id: str
    source_store_id: str
    destination_store_id: str
    transfer_quantity: int
    distance_km: float
    selected_partner: Optional[LogisticsPartnerEvaluation] = None
    reason: Optional[str] = None

class LogisticsOptionsResponse(BaseModel):
    sku_id: str
    source_store_id: str
    destination_store_id: str
    transfer_quantity: int
    matched: bool
    options: List[LogisticsPartnerEvaluation]

class LogisticsIntegrationResult(BaseModel):
    selected_partner: Optional[LogisticsPartnerEvaluation] = None
    delivery_cost: float
    eta_minutes: int

class IntegratedRecommendationResponse(BaseModel):
    decision: DecisionResponse
    logistics: Optional[LogisticsIntegrationResult] = None
    logistics_adjusted_net_recovery: float
    transfer_still_viable: bool
    reason: str

class LogisticsSummaryResponse(BaseModel):
    total_logistics_partners: int
    eligible_partner_evaluations: int
    rejected_partner_evaluations: int
    transfers_with_viable_partner: int
    transfers_with_no_viable_partner: int
    average_estimated_delivery_cost: float
    average_eta: float
    cold_chain_compatible_partners: int
