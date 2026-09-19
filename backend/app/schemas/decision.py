from enum import Enum
from pydantic import BaseModel
from typing import List, Optional
from .risk import RiskItem

class RecoveryActionType(str, Enum):
    TRANSFER = "TRANSFER"
    DISCOUNT = "DISCOUNT"
    BUNDLE = "BUNDLE"
    PROMOTE = "PROMOTE"
    RETURN = "RETURN"
    DISPOSE = "DISPOSE"
    NO_ACTION = "NO_ACTION"

class EvaluatedAction(BaseModel):
    action: RecoveryActionType
    available: bool
    quantity: int
    expected_recovered_value: float
    logistics_cost: float
    handling_cost: float
    risk_cost: float
    expected_net_recovery: float
    economically_viable: bool
    assumptions: List[str]
    reason: str

class DecisionResponse(BaseModel):
    sku_id: str
    store_id: str
    risk: Optional[RiskItem] = None
    actions: List[EvaluatedAction]
    selected_action: RecoveryActionType
    selected_destination_store_id: Optional[str] = None
    recommended_quantity: int
    expected_net_recovery: float
    decision_reason: str

class ActionComparisonResponse(BaseModel):
    sku_id: str
    store_id: str
    actions: List[EvaluatedAction]

class DecisionSummaryResponse(BaseModel):
    total_at_risk_items: int
    items_with_viable_recovery: int
    recommended_transfers: int
    recommended_discounts: int
    recommended_bundles: int
    recommended_promotions: int
    recommended_returns: int
    recommended_disposals: int
    no_action_items: int
    total_expected_net_recovery: float
