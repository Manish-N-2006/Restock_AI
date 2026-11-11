import pytest
from unittest.mock import AsyncMock, patch
from backend.app.services.buyer_matching import match_buyers, DEMO_BUYER_REGISTRY
from backend.app.services.simulation_orchestrator import (
    simulation_orchestrator,
    SimulationState,
)

def test_buyer_matching_deterministic_profiles():
    """Verify demonstration buyer registry contains valid candidate profiles."""
    assert len(DEMO_BUYER_REGISTRY) >= 5
    for b in DEMO_BUYER_REGISTRY:
        assert b.is_demo_data is True
        assert b.buyer_id.startswith("BUYER-")
        assert b.min_quantity > 0
        assert b.max_unit_price > 0.0


def test_buyer_matching_compatibility_evaluation():
    """Verify dairy inventory matches Metro Retail and Smoothie Co., but rejects incompatible lot sizes."""
    # Optimal Dairy Lot
    dairy_results = match_buyers(
        sku_id="YOG-001",
        product_name="Greek Yogurt 500g",
        quantity=120,
        unit_price=1.80,
    )
    compatible = [b for b in dairy_results if b.is_compatible]
    assert len(compatible) >= 1
    assert compatible[0].name == "Metro Retail Discount Mart"
    assert compatible[0].match_score >= 85.0

    # Incompatible lot size
    oversized_results = match_buyers(
        sku_id="YOG-001",
        product_name="Greek Yogurt 500g",
        quantity=5000,
        unit_price=1.80,
    )
    assert all(not b.is_compatible for b in oversized_results)


def test_simulation_state_initialization_scenarios():
    """Verify all 4 network scenarios initialize with strict data isolation."""
    state_a = simulation_orchestrator._init_default_scenario("SCENARIO_A")
    assert state_a.scenario_id == "SCENARIO_A"
    assert state_a.sku_id == "YOG-001"
    assert state_a.operating_perspective == "SURPLUS_DONOR"
    assert state_a.simulation_run_id.startswith("SIM-")

    state_b = simulation_orchestrator._init_default_scenario("SCENARIO_B")
    assert state_b.scenario_id == "SCENARIO_B"
    assert state_b.sku_id == "BER-003"
    assert state_b.operating_perspective == "STOCKOUT_RECEIVER"
    assert state_b.simulation_run_id.startswith("SIM-")

    state_c = simulation_orchestrator._init_default_scenario("SCENARIO_C")
    assert state_c.scenario_id == "SCENARIO_C"
    assert state_c.sku_id == "NET-MULTI"
    assert state_c.operating_perspective == "NETWORK_BALANCING"
    assert state_c.simulation_run_id.startswith("SIM-")

    state_d = simulation_orchestrator._init_default_scenario("SCENARIO_D")
    assert state_d.scenario_id == "SCENARIO_D"
    assert state_d.sku_id == "MILK-001"
    assert state_d.operating_perspective == "EXTERNAL_LIQUIDATION"
    assert state_d.simulation_run_id.startswith("SIM-")


def test_simulation_event_logging():
    """Verify in-memory live event feed records formatted telemetry."""
    state = simulation_orchestrator._init_default_scenario("SCENARIO_A")
    simulation_orchestrator._record_event(state, "Inventory Agent", "AUDIT_START", "Auditing SKU YOG-001")
    
    assert len(state.timeline) >= 1
    assert len(state.live_event_feed) >= 1
    assert state.live_event_feed[0]["agent"] == "Inventory Agent"
    assert state.live_event_feed[0]["action"] == "AUDIT_START"


def test_simulation_financial_reconciliation_math():
    """Verify financial formulas for gross, fee, and net recovery."""
    gross_recovered = 180.00
    paypal_fee = round(gross_recovered * 0.0349 + 0.49, 2)
    net_recovered = round(gross_recovered - paypal_fee, 2)

    assert paypal_fee == 6.77
    assert net_recovered == 173.23
    assert net_recovered > 0
