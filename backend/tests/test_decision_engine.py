from app.services.decision_engine import (
    evaluate_transfer,
    evaluate_discount,
    evaluate_bundle,
    evaluate_promote,
    evaluate_return,
    evaluate_dispose,
    evaluate_no_action,
    evaluate_decision,
    RecoveryActionType
)
from app.models.inventory import Inventory
from app.models.store import Store
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

def test_evaluate_discount():
    inv = Inventory(selling_price=100.0)
    action = evaluate_discount(inv, at_risk_quantity=100)
    
    assert action.action == RecoveryActionType.DISCOUNT
    assert action.available is True
    # 100 * 0.70 = 70 units
    assert action.quantity == 70
    # Price = 80. Value = 70 * 80 = 5600
    assert action.expected_recovered_value == 5600.0
    assert action.expected_net_recovery == 5600.0
    assert action.economically_viable is True

def test_evaluate_discount_low_qty():
    inv = Inventory(selling_price=100.0)
    action = evaluate_discount(inv, at_risk_quantity=1)
    
    assert action.available is False
    assert action.economically_viable is False
    assert action.quantity == 0

def test_evaluate_return_allowed():
    inv = Inventory(return_allowed=True, supplier_return_value=50.0)
    action = evaluate_return(inv, at_risk_quantity=100)
    
    assert action.available is True
    assert action.expected_recovered_value == 5000.0
    # logistics 30 + handling 15 = 45
    assert action.expected_net_recovery == 5000.0 - 45.0
    assert action.economically_viable is True

def test_evaluate_return_not_allowed():
    inv = Inventory(return_allowed=False)
    action = evaluate_return(inv, at_risk_quantity=100)
    
    assert action.available is False
    assert action.economically_viable is False

def test_evaluate_dispose():
    inv = Inventory()
    action = evaluate_dispose(inv, at_risk_quantity=100)
    
    assert action.available is True
    assert action.expected_recovered_value == 0.0
    # 100 * 5 = 500
    assert action.handling_cost == 500.0
    assert action.expected_net_recovery == -500.0
    assert action.economically_viable is False

def test_evaluate_promote():
    inv = Inventory(selling_price=100.0, daily_sales_7d=10.0)
    action = evaluate_promote(inv, at_risk_quantity=5)
    
    # uplift is 10 * 0.25 = 2.5 -> int() -> 2
    assert action.available is True
    assert action.quantity == 2
    assert action.expected_recovered_value == 200.0
    # handling = 15.0
    assert action.expected_net_recovery == 185.0
    assert action.economically_viable is True
