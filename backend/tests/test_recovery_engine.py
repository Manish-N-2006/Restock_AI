from app.schemas.recovery import RecoveryEvaluateRequest
from app.services.recovery_engine import evaluate_recovery_action

def test_profitable_transfer():
    req = RecoveryEvaluateRequest(
        sku_id="YOG-001",
        quantity=42,
        source_store_id="STORE_A",
        action="transfer",
        expected_recovery_price=160.0,
        logistics_cost=50.0,
        handling_cost=20.0,
        risk_cost=0.0
    )
    res = evaluate_recovery_action(req)
    assert res.expected_recovered_value == 42 * 160.0 # 6720
    assert res.expected_net_recovery == 6720.0 - 50.0 - 20.0 # 6650
    assert res.economically_viable is True

def test_unprofitable_transfer():
    req = RecoveryEvaluateRequest(
        sku_id="YOG-001",
        quantity=1,
        source_store_id="STORE_A",
        action="transfer",
        expected_recovery_price=160.0,
        logistics_cost=200.0, # High cost
        handling_cost=20.0,
        risk_cost=0.0
    )
    res = evaluate_recovery_action(req)
    assert res.expected_net_recovery == 160.0 - 220.0 # -60
    assert res.economically_viable is False

def test_discount():
    req = RecoveryEvaluateRequest(
        sku_id="YOG-001",
        quantity=42,
        source_store_id="STORE_A",
        action="discount",
        expected_recovery_price=100.0,
        logistics_cost=0.0,
        handling_cost=0.0,
        risk_cost=0.0
    )
    res = evaluate_recovery_action(req)
    assert res.expected_net_recovery == 4200.0
    assert res.economically_viable is True

def test_dispose():
    req = RecoveryEvaluateRequest(
        sku_id="YOG-001",
        quantity=42,
        source_store_id="STORE_A",
        action="dispose",
        expected_recovery_price=0.0,
        logistics_cost=0.0,
        handling_cost=50.0, # Cost to dispose
        risk_cost=0.0
    )
    res = evaluate_recovery_action(req)
    assert res.expected_net_recovery == -50.0
    assert res.economically_viable is False
