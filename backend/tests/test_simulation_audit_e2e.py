import pytest
import uuid
from unittest.mock import AsyncMock, patch
from backend.app.database import SessionLocal
from backend.app.models.inventory import Inventory
from backend.app.models.commerce import RecoveryOrder
from backend.app.payments.models import PaymentTransaction
from backend.app.services.simulation_orchestrator import (
    simulation_orchestrator,
    SimulationOrchestrator,
    SimulationState,
    SIMULATION_STEPS,
)
from backend.app.office.service import office_service

@pytest.mark.asyncio
async def test_audit_agent_identities():
    """Audit 1: Verify the exact 7 agent identities across workforce and office state."""
    assert len(office_service.agents) == 7
    expected = {
        1: ("Sarah Chen (CEO)", "Executive Operations", True),
        2: ("Marcus Vance (Inventory)", "Inventory Management", False),
        3: ("Elena Rostova (Strategy)", "Recovery Strategy", False),
        4: ("David Kim (Logistics)", "Logistics & Dispatch", False),
        5: ("Aisha Patel (Commerce)", "Commerce & Sales", False),
        6: ("Tom Becker (Fulfillment)", "Warehouse & Transit", False),
        7: ("Linda Zhang (Finance)", "Finance & Settlement", False),
    }
    for agent_id, (name, dept, is_lead) in expected.items():
        agent = office_service.agents[agent_id]
        assert agent.name == name, f"Agent {agent_id} name mismatch: {agent.name} vs {name}"
        assert agent.department == dept
        assert agent.is_team_lead is is_lead


@pytest.mark.asyncio
async def test_audit_scenario_a_surplus_transfer_no_paypal():
    """Audit 2: Scenario A - Surplus Inventory Rescue through all 9 stages with internal clearance (NO PayPal)."""
    sim = SimulationOrchestrator()
    state = await sim.reset_simulation("SCENARIO_A")
    run_id = state.simulation_run_id

    assert state.scenario_id == "SCENARIO_A"
    assert state.sku_id == "YOG-001"
    assert state.current_step_index == 0

    # Stage 1: Inventory Discovery (Surplus)
    s1 = await sim.execute_step(run_id)
    assert s1.current_step_index == 1
    assert s1.inventory_discovery is not None
    assert s1.inventory_discovery["at_risk_quantity"] > 0
    assert any("Marcus Vance" in ev["agent"] for ev in s1.live_event_feed)

    # Stage 2: Network Matching (Candidate Receivers)
    s2 = await sim.execute_step(run_id)
    assert s2.current_step_index == 2
    assert s2.candidate_branches is not None
    assert len(s2.candidate_branches) >= 1
    assert any("Elena Rostova" in ev["agent"] for ev in s2.live_event_feed)

    # Stage 3: Strategy & Economics
    s3 = await sim.execute_step(run_id)
    assert s3.current_step_index == 3
    assert s3.network_economics is not None
    assert s3.network_economics["net_incremental_network_value"] > 0

    # Stage 4: Logistics Optimization
    s4 = await sim.execute_step(run_id)
    assert s4.current_step_index == 4
    assert s4.logistics_comparison is not None
    assert any("David Kim" in ev["agent"] for ev in s4.live_event_feed)

    # Stage 5: Transfer Manifest
    s5 = await sim.execute_step(run_id)
    assert s5.current_step_index == 5
    assert s5.offer_creation is not None
    assert s5.offer_creation["type"] == "TRANSFER_MANIFEST"

    # Stage 6: Human Approval (Cedar) with auto_approve = False
    s6 = await sim.execute_step(run_id)
    assert s6.status == "AWAITING_APPROVAL"
    assert s6.human_approval is not None

    # Resumed via Manager Approval (Cedar Gate Cleared -> Executes Stage 7 Settlement)
    s6_resumed = await sim.approve_pending_decision(run_id, decision="APPROVED")
    assert s6_resumed.status == "RUNNING"
    assert s6_resumed.human_approval["status"] == "MANAGER_APPROVED"
    assert any("Sarah Chen" in ev["agent"] for ev in s6_resumed.live_event_feed)

    # Stage 7: Settlement Check -> MUST BE NOT_APPLICABLE for internal transfers
    assert s6_resumed.paypal_checkout["status"] == "NOT_APPLICABLE"
    assert "internal" in s6_resumed.paypal_checkout["details"].lower()

    # Stage 8: Fulfillment
    s8 = await sim.execute_step(run_id)
    assert s8.fulfillment is not None
    assert s8.fulfillment["status"] in ("IN_TRANSIT", "DISPATCHED", "FULFILLED")
    assert any("Tom Becker" in ev["agent"] for ev in s8.live_event_feed)

    # Stage 9: Financial Reconciliation & Final CEO Report
    s9 = await sim.execute_step(run_id)
    assert s9.status == "COMPLETED"
    assert s9.financial_reconciliation["status"] == "RECONCILED"
    assert s9.ceo_report is not None
    assert s9.ceo_report["governance_status"] == "APPROVED"
    assert any("Linda Zhang" in ev["agent"] for ev in s9.live_event_feed)


@pytest.mark.asyncio
async def test_audit_scenario_b_stockout_prevention_no_paypal():
    """Audit 3: Scenario B - Stockout Prevention receiving branch perspective, saving over supplier rush order."""
    sim = SimulationOrchestrator()
    state = await sim.reset_simulation("SCENARIO_B")
    run_id = state.simulation_run_id

    # Advance through Stage 1 & 2
    s1 = await sim.execute_step(run_id)
    assert s1.inventory_discovery["risk_level"] == "CRITICAL_SHORTAGE"

    s2 = await sim.execute_step(run_id)
    assert s2.candidate_branches is not None
    assert len(s2.candidate_branches) >= 1

    # Stage 3: Economics comparison
    s3 = await sim.execute_step(run_id)
    assert s3.network_economics is not None
    assert s3.network_economics["supplier_replenishment_comparison"]["internal_transfer_advantage"] > 0

    # Advance to approval and approve
    while s3.current_step_index < 5:
        s3 = await sim.execute_step(run_id)
    s_app = await sim.execute_step(run_id)
    assert s_app.status == "AWAITING_APPROVAL"
    s_resumed = await sim.approve_pending_decision(run_id, decision="APPROVED")

    # Settlement must be internal (NOT_APPLICABLE for PayPal)
    s7 = await sim.execute_step(run_id)
    assert s7.paypal_checkout["status"] == "NOT_APPLICABLE"


@pytest.mark.asyncio
async def test_audit_scenario_c_network_balancing_matrix():
    """Audit 4: Scenario C - Multi-branch inventory balancing matrix across 4 branches."""
    sim = SimulationOrchestrator()
    state = await sim.reset_simulation("SCENARIO_C")
    run_id = state.simulation_run_id

    # Stage 1: Inventory Discovery
    s1 = await sim.execute_step(run_id)
    assert s1.inventory_discovery["risk_level"] == "NETWORK_IMBALANCE"

    # Stage 2: Greedy Multi-Branch Balancing Plan
    s2 = await sim.execute_step(run_id)
    assert s2.network_balance_plan is not None
    assert s2.network_balance_plan["total_units_rebalanced"] == 110
    assert len(s2.network_balance_plan["transfers"]) == 2


@pytest.mark.asyncio
async def test_audit_scenario_d_external_liquidation_paypal():
    """Audit 5: Scenario D - External B2B Liquidation Fallback with genuine PayPal Sandbox checkout."""
    sim = SimulationOrchestrator()
    state = await sim.reset_simulation("SCENARIO_D")
    run_id = state.simulation_run_id

    # Stage 1: Critical expiry surplus
    s1 = await sim.execute_step(run_id)
    assert s1.inventory_discovery["risk_level"] == "CRITICAL_EXPIRY"

    # Stage 2: B2B Commercial Buyer discovery
    s2 = await sim.execute_step(run_id)
    assert s2.buyer_discovery is not None
    assert s2.buyer_discovery["top_matched_buyer"]["name"] == "Metro Retail Discount Mart"

    # Advance through Stage 3, 4, 5 to approval
    while s2.current_step_index < 5:
        s2 = await sim.execute_step(run_id)

    # Stage 6: Human Approval
    s6 = await sim.execute_step(run_id)
    assert s6.status == "AWAITING_APPROVAL"
    s6_res = await sim.approve_pending_decision(run_id, decision="APPROVED")

    # Stage 7: Genuine PayPal checkout awaiting payment
    s7 = await sim.execute_step(run_id)
    assert s7.status == "AWAITING_PAYMENT"
    assert s7.paypal_checkout["status"] in ("AWAITING_BUYER_APPROVAL", "PENDING_PAYMENT")

    # Capture PayPal payment
    s7_cap = await sim.confirm_paypal_capture(
        run_id=run_id,
        paypal_order_id="TEST-PAYPAL-ORD-D",
        paypal_capture_id="CAP-TEST-D-999",
        amount=216.00,
        currency="USD"
    )
    assert s7_cap.paypal_checkout["status"] == "CAPTURED"
    assert s7_cap.paypal_checkout["paypal_capture_id"] == "CAP-TEST-D-999"


@pytest.mark.asyncio
async def test_audit_simulation_data_isolation():
    """Audit 5: Simulation data isolation - Database tables remain untouched across multiple runs and resets."""
    # Count rows before simulation runs
    with SessionLocal() as db:
        initial_inv_count = db.query(Inventory).count()
        initial_rec_order_count = db.query(RecoveryOrder).count()
        initial_txn_count = db.query(PaymentTransaction).count()

    sim = SimulationOrchestrator()

    # Run multiple parallel scenarios
    s1 = await sim.reset_simulation("SCENARIO_A")
    s2 = await sim.reset_simulation("SCENARIO_B")
    s3 = await sim.reset_simulation("SCENARIO_C")
    run1 = s1.simulation_run_id
    run2 = s2.simulation_run_id
    run3 = s3.simulation_run_id

    assert run1 != run2 != run3, "Simulation run IDs must be unique"

    # Step through all 3 runs
    for run in [run1, run2, run3]:
        for _ in range(3):
            await sim.execute_step(run)

    # Reset simulation
    reset_state = await sim.reset_simulation("SCENARIO_A")
    assert reset_state.current_step_index == 0
    assert reset_state.status == "IDLE"

    # Verify real database tables have NOT mutated by a single row
    with SessionLocal() as db:
        final_inv_count = db.query(Inventory).count()
        final_rec_order_count = db.query(RecoveryOrder).count()
        final_txn_count = db.query(PaymentTransaction).count()

    assert final_inv_count == initial_inv_count, "Real inventory table mutated during simulation!"
    assert final_rec_order_count == initial_rec_order_count, "Real recovery orders table mutated during simulation!"
    assert final_txn_count == initial_txn_count, "Real payment transactions table mutated during simulation!"
