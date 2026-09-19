from pydantic import BaseModel
from typing import Literal

class RecoveryEvaluateRequest(BaseModel):
    sku_id: str
    quantity: int
    source_store_id: str
    action: Literal["transfer", "discount", "dispose", "bundle", "promote", "return"]
    expected_recovery_price: float = 0.0
    logistics_cost: float = 0.0
    handling_cost: float = 0.0
    risk_cost: float = 0.0

class RecoveryEvaluateResponse(BaseModel):
    action: str
    quantity: int
    expected_recovered_value: float
    logistics_cost: float
    handling_cost: float
    risk_cost: float
    expected_net_recovery: float
    economically_viable: bool
