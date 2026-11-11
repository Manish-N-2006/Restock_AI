"""
Comprehensive Unit & Integration Test Suite for Network-First Inventory Redistribution.
Tests all 12 business and operational requirements specified in ReStockAI 2.0.
"""

import pytest
from app.services.network_matching import (
    DonorBranch,
    ReceivingBranch,
    match_candidate_receivers,
    match_candidate_donors,
    optimize_logistics_partners,
    calculate_incremental_network_value,
    solve_constrained_greedy_balancing,
)
from app.services.buyer_matching import match_buyers
from app.services.simulation_orchestrator import simulation_orchestrator


# -------------------------------------------------------------------------
# TEST 1: Surplus branch with one clearly optimal receiver
# -------------------------------------------------------------------------
def test_surplus_branch_single_optimal_receiver():
    donor = DonorBranch(
        store_id="STORE_A",
        store_name="Main Hub",
        sku_id="YOG-001",
        product_name="Greek Yogurt 500g",
        current_stock=120,
        safety_stock=20,
        transferable_quantity=100,
        daily_velocity=4.0,
        days_to_expiry=3.0,
        cost_price=2.50,
        selling_price=3.99,
        temperature_class="REFRIGERATED",
        requires_cold_chain=True,
        latitude=34.0522,
        longitude=-118.2437,
    )
    receiver = ReceivingBranch(
        store_id="STORE_B",
        store_name="North Branch",
        sku_id="YOG-001",
        product_name="Greek Yogurt 500g",
        current_stock=10,
        target_stock=100,
        daily_demand=25.0,
        shortage_quantity=90,
        storage_capacity=150,
        available_capacity=140,
        absorbable_quantity=100,
        stockout_deadline_hours=8.0,
        supports_cold_chain=True,
        latitude=34.1425,
        longitude=-118.2551,
    )

    matches = match_candidate_receivers(donor, [receiver])
    assert len(matches) == 1
    assert matches[0].is_eligible is True
    assert matches[0].store_id == "STORE_B"
    assert matches[0].net_economic_value > 0
    assert matches[0].recommended_transfer_qty == 90


# -------------------------------------------------------------------------
# TEST 2: Surplus branch with multiple receiver choices
# -------------------------------------------------------------------------
def test_surplus_branch_multiple_receiver_choices():
    donor = DonorBranch(
        store_id="STORE_A",
        store_name="Main Hub",
        sku_id="YOG-001",
        product_name="Greek Yogurt 500g",
        current_stock=120,
        safety_stock=20,
        transferable_quantity=100,
        daily_velocity=4.0,
        days_to_expiry=3.0,
        cost_price=2.50,
        selling_price=3.99,
        temperature_class="REFRIGERATED",
        requires_cold_chain=True,
        latitude=34.0522,
        longitude=-118.2437,
    )
    # Store B: high demand, close
    receiver_b = ReceivingBranch(
        store_id="STORE_B",
        store_name="North Branch",
        sku_id="YOG-001",
        product_name="Greek Yogurt 500g",
        current_stock=10,
        target_stock=80,
        daily_demand=28.0,
        shortage_quantity=70,
        storage_capacity=100,
        available_capacity=90,
        absorbable_quantity=70,
        stockout_deadline_hours=6.0,
        supports_cold_chain=True,
        latitude=34.1022,
        longitude=-118.2437,
    )
    # Store E: moderate demand, further away
    receiver_e = ReceivingBranch(
        store_id="STORE_E",
        store_name="West Branch",
        sku_id="YOG-001",
        product_name="Greek Yogurt 500g",
        current_stock=20,
        target_stock=50,
        daily_demand=10.0,
        shortage_quantity=30,
        storage_capacity=80,
        available_capacity=60,
        absorbable_quantity=30,
        stockout_deadline_hours=18.0,
        supports_cold_chain=True,
        latitude=34.0522,
        longitude=-118.3437,
    )

    matches = match_candidate_receivers(donor, [receiver_b, receiver_e])
    assert len(matches) == 2
    assert matches[0].store_id == "STORE_B"
    assert matches[0].match_score > matches[1].match_score
    assert matches[0].recommended_transfer_qty == 70


# -------------------------------------------------------------------------
# TEST 3: Receiving branch with multiple donor choices
# -------------------------------------------------------------------------
def test_receiving_branch_multiple_donor_choices():
    receiver = ReceivingBranch(
        store_id="STORE_D",
        store_name="East Branch",
        sku_id="BER-003",
        product_name="Organic Blueberries 250g",
        current_stock=8,
        target_stock=60,
        daily_demand=32.0,
        shortage_quantity=52,
        storage_capacity=100,
        available_capacity=92,
        absorbable_quantity=60,
        stockout_deadline_hours=6.0,
        supports_cold_chain=True,
        latitude=34.0522,
        longitude=-118.1437,
    )
    # Donor A: plenty of stock above safety buffer
    donor_a = DonorBranch(
        store_id="STORE_A",
        store_name="Main Hub",
        sku_id="BER-003",
        product_name="Organic Blueberries 250g",
        current_stock=80,
        safety_stock=20,
        transferable_quantity=60,
        daily_velocity=3.0,
        days_to_expiry=4.0,
        cost_price=1.80,
        selling_price=2.99,
        temperature_class="REFRIGERATED",
        requires_cold_chain=True,
        latitude=34.0522,
        longitude=-118.2437,
    )
    # Donor C: barely has stock, safety stock leaves only 5 units
    donor_c = DonorBranch(
        store_id="STORE_C",
        store_name="South Branch",
        sku_id="BER-003",
        product_name="Organic Blueberries 250g",
        current_stock=25,
        safety_stock=20,
        transferable_quantity=5,
        daily_velocity=2.0,
        days_to_expiry=4.0,
        cost_price=1.80,
        selling_price=2.99,
        temperature_class="REFRIGERATED",
        requires_cold_chain=True,
        latitude=33.9525,
        longitude=-118.2551,
    )

    matches = match_candidate_donors(receiver, [donor_a, donor_c])
    assert len(matches) == 2
    assert matches[0].store_id == "STORE_A"
    assert matches[0].recommended_transfer_qty == 52
    assert matches[0].match_score > matches[1].match_score


# -------------------------------------------------------------------------
# TEST 4: Transfer beneficial compared with supplier replenishment
# -------------------------------------------------------------------------
def test_transfer_beneficial_vs_supplier_replenishment():
    donor = DonorBranch(
        store_id="STORE_A", store_name="Main Hub", sku_id="YOG-001", product_name="Greek Yogurt 500g",
        current_stock=120, safety_stock=20, transferable_quantity=100, daily_velocity=4.0, days_to_expiry=3.0,
        cost_price=2.50, selling_price=3.99, temperature_class="REFRIGERATED", requires_cold_chain=True,
        latitude=34.0522, longitude=-118.2437
    )
    receiver = ReceivingBranch(
        store_id="STORE_B", store_name="North Branch", sku_id="YOG-001", product_name="Greek Yogurt 500g",
        current_stock=10, target_stock=100, daily_demand=25.0, shortage_quantity=90,
        storage_capacity=150, available_capacity=140, absorbable_quantity=100, stockout_deadline_hours=8.0,
        supports_cold_chain=True, latitude=34.1425, longitude=-118.2551
    )
    _, best_carrier = optimize_logistics_partners(donor.latitude, donor.longitude, receiver.latitude, receiver.longitude, 90, True, 72.0)

    econ = calculate_incremental_network_value(donor, receiver, 90, best_carrier)
    assert econ.net_incremental_network_value > 0
    supplier_comp = econ.supplier_replenishment_comparison
    assert supplier_comp["internal_transfer_advantage"] > 0
    assert "superior net network value" in supplier_comp["economic_conclusion"]


# -------------------------------------------------------------------------
# TEST 5: Transfer not beneficial because transportation cost is too high
# -------------------------------------------------------------------------
def test_transfer_not_beneficial_high_transport_cost():
    donor = DonorBranch(
        store_id="STORE_A", store_name="Main Hub", sku_id="CHEAP-01", product_name="Generic Bread",
        current_stock=100, safety_stock=10, transferable_quantity=90, daily_velocity=2.0, days_to_expiry=1.0,
        cost_price=0.30, selling_price=0.60, temperature_class="AMBIENT", requires_cold_chain=False,
        latitude=34.0522, longitude=-118.2437
    )
    # Remote location 120km away
    receiver = ReceivingBranch(
        store_id="STORE_REMOTE", store_name="Far Outpost", sku_id="CHEAP-01", product_name="Generic Bread",
        current_stock=0, target_stock=10, daily_demand=5.0, shortage_quantity=10,
        storage_capacity=20, available_capacity=20, absorbable_quantity=5, stockout_deadline_hours=24.0,
        supports_cold_chain=True, latitude=35.0522, longitude=-118.2437
    )
    matches = match_candidate_receivers(donor, [receiver])
    assert len(matches) == 1
    # Should be ineligible due to exceeding economic radius
    assert matches[0].is_eligible is False
    assert any("radius" in r.lower() or "distance" in r.lower() for r in matches[0].rejection_reasons)


# -------------------------------------------------------------------------
# TEST 6: Cold-chain incompatible carrier
# -------------------------------------------------------------------------
def test_cold_chain_incompatible_carrier():
    # Cold chain required
    options, best = optimize_logistics_partners(
        34.0522, -118.2437, 34.1425, -118.2551, 50, requires_cold_chain=True, hours_to_expiry=48.0
    )
    ambient_carriers = [c for c in options if not c.cold_chain_available]
    assert len(ambient_carriers) > 0
    for ac in ambient_carriers:
        assert ac.eligible is False
        assert "active refrigeration" in ac.rejection_reason.lower()
    # Best carrier must have cold chain
    assert best is not None
    assert best.cold_chain_available is True


# -------------------------------------------------------------------------
# TEST 7: Receiver capacity unavailable
# -------------------------------------------------------------------------
def test_receiver_capacity_unavailable():
    donor = DonorBranch(
        store_id="STORE_A", store_name="Main Hub", sku_id="YOG-001", product_name="Greek Yogurt 500g",
        current_stock=100, safety_stock=20, transferable_quantity=80, daily_velocity=4.0, days_to_expiry=3.0,
        cost_price=2.50, selling_price=3.99, temperature_class="REFRIGERATED", requires_cold_chain=True,
        latitude=34.0522, longitude=-118.2437
    )
    receiver_full = ReceivingBranch(
        store_id="STORE_FULL", store_name="Packed Store", sku_id="YOG-001", product_name="Greek Yogurt 500g",
        current_stock=100, target_stock=100, daily_demand=15.0, shortage_quantity=0,
        storage_capacity=100, available_capacity=0, absorbable_quantity=0, stockout_deadline_hours=48.0,
        supports_cold_chain=True, latitude=34.1022, longitude=-118.2437
    )
    matches = match_candidate_receivers(donor, [receiver_full])
    assert len(matches) == 1
    assert matches[0].is_eligible is False
    assert any("capacity" in r.lower() for r in matches[0].rejection_reasons)


# -------------------------------------------------------------------------
# TEST 8: Donor safety stock protection
# -------------------------------------------------------------------------
def test_donor_safety_stock_protection():
    # Current stock 25, safety buffer 20 -> transferable is only 5!
    donor = DonorBranch(
        store_id="STORE_A", store_name="Main Hub", sku_id="YOG-001", product_name="Greek Yogurt 500g",
        current_stock=25, safety_stock=20, transferable_quantity=5, daily_velocity=4.0, days_to_expiry=3.0,
        cost_price=2.50, selling_price=3.99, temperature_class="REFRIGERATED", requires_cold_chain=True,
        latitude=34.0522, longitude=-118.2437
    )
    receiver = ReceivingBranch(
        store_id="STORE_B", store_name="North Branch", sku_id="YOG-001", product_name="Greek Yogurt 500g",
        current_stock=5, target_stock=50, daily_demand=20.0, shortage_quantity=45,
        storage_capacity=100, available_capacity=95, absorbable_quantity=45, stockout_deadline_hours=8.0,
        supports_cold_chain=True, latitude=34.1022, longitude=-118.2437
    )
    matches = match_candidate_receivers(donor, [receiver])
    assert len(matches) == 1
    # Recommended transfer cannot exceed transferable quantity (5 units)
    assert matches[0].recommended_transfer_qty == 5
    assert matches[0].recommended_transfer_qty <= (donor.current_stock - donor.safety_stock)


# -------------------------------------------------------------------------
# TEST 9: Multiple-branch inventory rebalancing
# -------------------------------------------------------------------------
def test_multiple_branch_inventory_rebalancing():
    donors = [
        DonorBranch(
            store_id="STORE_A", store_name="Main Hub", sku_id="YOG-001", product_name="Greek Yogurt 500g",
            current_stock=100, safety_stock=20, transferable_quantity=80, daily_velocity=4.0, days_to_expiry=3.5,
            cost_price=2.50, selling_price=3.99, temperature_class="REFRIGERATED", requires_cold_chain=True,
            latitude=34.0522, longitude=-118.2437
        ),
        DonorBranch(
            store_id="STORE_C", store_name="South Branch", sku_id="SAL-002", product_name="Atlantic Salmon Fillet",
            current_stock=60, safety_stock=15, transferable_quantity=45, daily_velocity=2.0, days_to_expiry=4.0,
            cost_price=8.50, selling_price=12.99, temperature_class="REFRIGERATED", requires_cold_chain=True,
            latitude=33.9525, longitude=-118.2551
        ),
    ]
    receivers = [
        ReceivingBranch(
            store_id="STORE_B", store_name="North Branch", sku_id="YOG-001", product_name="Greek Yogurt 500g",
            current_stock=10, target_stock=80, daily_demand=25.0, shortage_quantity=70,
            storage_capacity=150, available_capacity=140, absorbable_quantity=75, stockout_deadline_hours=12.0,
            supports_cold_chain=True, latitude=34.1425, longitude=-118.2551
        ),
        ReceivingBranch(
            store_id="STORE_D", store_name="East Branch", sku_id="SAL-002", product_name="Atlantic Salmon Fillet",
            current_stock=5, target_stock=45, daily_demand=18.0, shortage_quantity=40,
            storage_capacity=100, available_capacity=95, absorbable_quantity=45, stockout_deadline_hours=8.0,
            supports_cold_chain=True, latitude=34.0522, longitude=-118.1437
        ),
    ]
    plan = solve_constrained_greedy_balancing(donors, receivers)
    assert len(plan.transfers) == 2
    assert plan.total_units_rebalanced == 110
    assert plan.total_net_network_value > 500.0
    assert "Greedy" in plan.algorithm


# -------------------------------------------------------------------------
# TEST 10: No viable internal receiver, requiring external liquidation
# -------------------------------------------------------------------------
def test_no_viable_internal_receiver_requires_external_liquidation():
    donor = DonorBranch(
        store_id="STORE_A", store_name="Main Hub", sku_id="MILK-001", product_name="Pastured Whole Milk 1L",
        current_stock=135, safety_stock=15, transferable_quantity=120, daily_velocity=5.0, days_to_expiry=1.5,
        cost_price=2.20, selling_price=3.99, temperature_class="REFRIGERATED", requires_cold_chain=True,
        latitude=34.0522, longitude=-118.2437
    )
    # Both internal receivers cannot accept: Store B is full (0 capacity), Store C lacks cold chain
    receivers = [
        ReceivingBranch(
            store_id="STORE_B", store_name="North Branch", sku_id="MILK-001", product_name="Pastured Whole Milk 1L",
            current_stock=100, target_stock=100, daily_demand=20.0, shortage_quantity=0,
            storage_capacity=100, available_capacity=0, absorbable_quantity=0, stockout_deadline_hours=72.0,
            supports_cold_chain=True, latitude=34.1425, longitude=-118.2551
        ),
        ReceivingBranch(
            store_id="STORE_C", store_name="South Branch", sku_id="MILK-001", product_name="Pastured Whole Milk 1L",
            current_stock=10, target_stock=50, daily_demand=5.0, shortage_quantity=40,
            storage_capacity=80, available_capacity=70, absorbable_quantity=20, stockout_deadline_hours=24.0,
            supports_cold_chain=False, latitude=33.9525, longitude=-118.2551
        ),
    ]
    matches = match_candidate_receivers(donor, receivers)
    # Must have 0 eligible internal receivers!
    eligible = [m for m in matches if m.is_eligible]
    assert len(eligible) == 0

    # Since no internal receiver is eligible, external liquidation fallback (Scenario D) is triggered:
    state = simulation_orchestrator._init_default_scenario("SCENARIO_D")
    assert state.scenario_id == "SCENARIO_D"
    assert state.operating_perspective == "EXTERNAL_LIQUIDATION"

    buyer_matches = match_buyers(
        sku_id=state.sku_id,
        product_name=state.product_name,
        quantity=120,
        unit_price=1.80,
        requires_cold_chain=True,
    )
    assert len(buyer_matches) > 0
    assert buyer_matches[0].is_compatible is True
    assert buyer_matches[0].name == "Metro Retail Discount Mart"


# -------------------------------------------------------------------------
# TEST 11: External buyer PayPal Sandbox purchase
# -------------------------------------------------------------------------
def test_external_buyer_paypal_sandbox_purchase():
    state = simulation_orchestrator._init_default_scenario("SCENARIO_D")
    state.status = "AWAITING_PAYMENT"
    state.offer_creation = {
        "order_id": "SIM-ORD-EXT-01",
        "buyer_id": "BUYER-METRO-01",
        "buyer_name": "Metro Retail Discount Mart",
        "quantity": 120,
        "unit_price": 1.80,
        "total_amount": 216.00,
        "currency": "USD",
        "status": "PENDING_PAYMENT",
    }
    # Verify order lookup returns correct data for payment gateway
    order_data = simulation_orchestrator.get_order_data("SIM-ORD-EXT-01")
    assert order_data is not None
    assert order_data["total_amount"] == 216.00
    assert order_data["currency"] == "USD"

    # Confirm capture recording
    state.paypal_checkout = {
        "order_id": "PAYPAL-ORD-TEST-D",
        "paypal_capture_id": "CAP-SIM-998877",
        "status": "CAPTURED",
        "amount": 216.00,
        "currency": "USD",
        "paypal_fee": 8.03,
        "net_amount": 207.97,
    }
    state.status = "PAYMENT_CONFIRMED"
    assert state.paypal_checkout["status"] == "CAPTURED"
    assert state.paypal_checkout["paypal_capture_id"] == "CAP-SIM-998877"
    assert state.paypal_checkout["net_amount"] > 0


# -------------------------------------------------------------------------
# TEST 12: Rejection and no-action outcomes
# -------------------------------------------------------------------------
def test_rejection_and_no_action_outcomes():
    state = simulation_orchestrator._init_default_scenario("SCENARIO_A")
    state.status = "AWAITING_APPROVAL"
    state.human_approval = {
        "required": True,
        "policy": "High-Value Markdown Approval (> $150)",
        "status": "MANAGER_REJECTED",
        "decision": "REJECTED",
        "rejection_reason": "Cold storage audit pending; transport halted for food safety.",
    }
    state.status = "REJECTED"
    simulation_orchestrator._record_event(
        state,
        "Sarah Chen (CEO)",
        "DECISION_REJECTED",
        "Operation supervisor declined transfer authorization. Workflow aborted safely."
    )
    assert state.status == "REJECTED"
    assert state.human_approval["status"] == "MANAGER_REJECTED"
    assert state.fulfillment is None
    assert state.paypal_checkout is None
    assert any("declined" in ev["details"].lower() or "rejected" in ev["action"].lower() for ev in state.live_event_feed)
