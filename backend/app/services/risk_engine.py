import math
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from ..models.inventory import Inventory
from ..schemas.risk import RiskItem, RiskResponse, RiskSummaryResponse

def calculate_inventory_risk(record: Inventory) -> RiskItem:
    today = datetime.utcnow()
    # Days to expiry
    if record.expiry_date:
        days_to_expiry = (record.expiry_date - today).days
        days_to_expiry = max(days_to_expiry, 0)
    else:
        days_to_expiry = 9999

    # Expected sales before expiry
    expected_sales_before_expiry = record.daily_sales_7d * days_to_expiry

    # Expected remaining quantity
    expected_remaining_quantity = max(record.quantity - expected_sales_before_expiry, 0)

    # At-risk quantity (do not exceed available quantity)
    at_risk_quantity = min(expected_remaining_quantity, record.quantity)
    at_risk_quantity = math.floor(at_risk_quantity)

    # At-risk value
    at_risk_value = at_risk_quantity * record.cost_price

    # Risk percentage
    risk_percentage = (at_risk_quantity / record.quantity * 100) if record.quantity > 0 else 0.0

    # Risk Score (normalized 0 to 100)
    # Higher score when expiry is closer, remaining quantity is larger, sales velocity is low
    # Formula: Base on risk percentage, then scale by urgency.
    # Urgency factor: if days_to_expiry <= 3, it's very urgent.
    urgency_factor = 1.0
    if days_to_expiry <= 3:
        urgency_factor = 1.5
    elif days_to_expiry <= 7:
        urgency_factor = 1.2
        
    raw_score = risk_percentage * urgency_factor
    risk_score = min(round(raw_score, 2), 100.0)

    # Risk Level classification
    if risk_score >= 80 or (days_to_expiry <= 2 and record.quantity > 0):
        risk_level = "CRITICAL"
    elif risk_score >= 50:
        risk_level = "HIGH"
    elif risk_score >= 20:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
        
    return RiskItem(
        sku_id=record.sku_id,
        product_name=record.product_name,
        store_id=record.store_id,
        quantity=record.quantity,
        days_to_expiry=days_to_expiry,
        daily_sales_7d=record.daily_sales_7d,
        expected_sales_before_expiry=expected_sales_before_expiry,
        expected_remaining_quantity=math.floor(expected_remaining_quantity),
        at_risk_quantity=at_risk_quantity,
        at_risk_value=at_risk_value,
        risk_percentage=round(risk_percentage, 2),
        risk_score=risk_score,
        risk_level=risk_level
    )

def evaluate_all_risks(db: Session) -> RiskResponse:
    records = db.query(Inventory).all()
    items = [calculate_inventory_risk(r) for r in records]
    return RiskResponse(items=items)

def get_risk_summary(db: Session) -> RiskSummaryResponse:
    records = db.query(Inventory).all()
    risk_items = [calculate_inventory_risk(r) for r in records]
    
    total_inventory_units = sum(r.quantity for r in records)
    total_inventory_value = sum(r.quantity * r.cost_price for r in records)
    
    total_at_risk_units = sum(ri.at_risk_quantity for ri in risk_items)
    total_at_risk_value = sum(ri.at_risk_value for ri in risk_items)
    
    high_critical_count = sum(1 for ri in risk_items if ri.risk_level in ["HIGH", "CRITICAL"])
    
    percentage_at_risk = (total_at_risk_units / total_inventory_units * 100) if total_inventory_units > 0 else 0.0
    
    return RiskSummaryResponse(
        total_inventory_units=total_inventory_units,
        total_inventory_value=total_inventory_value,
        total_at_risk_units=total_at_risk_units,
        total_at_risk_value=total_at_risk_value,
        high_critical_count=high_critical_count,
        percentage_at_risk=round(percentage_at_risk, 2)
    )
