from datetime import datetime, timedelta
from app.models.inventory import Inventory
from app.services.risk_engine import calculate_inventory_risk

def test_risk_normal_inventory():
    # Can completely sell before expiry
    inv = Inventory(
        sku_id="TEST-1",
        product_name="Test Product 1",
        store_id="STORE_A",
        quantity=50,
        cost_price=10.0,
        expiry_date=datetime.utcnow() + timedelta(days=20),
        daily_sales_7d=5.0
    )
    risk = calculate_inventory_risk(inv)
    assert risk.expected_sales_before_expiry >= 95.0
    assert risk.expected_remaining_quantity == 0
    assert risk.at_risk_quantity == 0
    assert risk.at_risk_value == 0.0
    assert risk.risk_percentage == 0.0
    assert risk.risk_level == "LOW"

def test_risk_near_expiry():
    # Yogurt scenario: 50 units, 4 daily sales, 2 days to expiry
    inv = Inventory(
        sku_id="YOG-001",
        product_name="Yogurt 500g",
        store_id="STORE_A",
        quantity=50,
        cost_price=120.0,
        expiry_date=datetime.utcnow() + timedelta(days=2, minutes=5),
        daily_sales_7d=4.0
    )
    risk = calculate_inventory_risk(inv)
    assert risk.expected_sales_before_expiry == 8.0
    assert risk.expected_remaining_quantity == 42
    assert risk.at_risk_quantity == 42
    assert risk.at_risk_value == 42 * 120.0
    assert risk.risk_percentage == 84.0
    assert risk.risk_level == "CRITICAL" # because expiry <= 2 days

def test_zero_daily_sales():
    inv = Inventory(
        sku_id="TEST-2",
        product_name="Test Product 2",
        store_id="STORE_A",
        quantity=30,
        cost_price=10.0,
        expiry_date=datetime.utcnow() + timedelta(days=10),
        daily_sales_7d=0.0
    )
    risk = calculate_inventory_risk(inv)
    assert risk.expected_sales_before_expiry == 0.0
    assert risk.at_risk_quantity == 30
    assert risk.risk_percentage == 100.0

def test_zero_quantity():
    inv = Inventory(
        sku_id="TEST-3",
        product_name="Test Product 3",
        store_id="STORE_A",
        quantity=0,
        cost_price=10.0,
        expiry_date=datetime.utcnow() + timedelta(days=10),
        daily_sales_7d=5.0
    )
    risk = calculate_inventory_risk(inv)
    assert risk.risk_percentage == 0.0
    assert risk.at_risk_quantity == 0
    assert risk.risk_level == "LOW"

def test_expired_inventory():
    inv = Inventory(
        sku_id="TEST-4",
        product_name="Test Product 4",
        store_id="STORE_A",
        quantity=10,
        cost_price=10.0,
        expiry_date=datetime.utcnow() - timedelta(days=2),
        daily_sales_7d=5.0
    )
    risk = calculate_inventory_risk(inv)
    assert risk.days_to_expiry == 0
    assert risk.at_risk_quantity == 10
    assert risk.risk_level == "CRITICAL"
