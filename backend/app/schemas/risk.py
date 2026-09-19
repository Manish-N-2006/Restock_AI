from pydantic import BaseModel
from typing import List
from .inventory import Inventory

class RiskItem(BaseModel):
    sku_id: str
    product_name: str
    store_id: str
    quantity: int
    days_to_expiry: int
    daily_sales_7d: float
    expected_sales_before_expiry: float
    expected_remaining_quantity: int
    at_risk_quantity: int
    at_risk_value: float
    risk_percentage: float
    risk_score: float
    risk_level: str

class RiskResponse(BaseModel):
    items: List[RiskItem]

class RiskSummaryResponse(BaseModel):
    total_inventory_units: int
    total_inventory_value: float
    total_at_risk_units: int
    total_at_risk_value: float
    high_critical_count: int
    percentage_at_risk: float
