"""
Simulation Orchestration Service 2.0 — Network-First Inventory Intelligence & Recovery.

Coordinates internal multi-branch redistribution, donor/receiver matching,
incremental network economics, road-network logistics optimization, Cedar authorization,
and external B2B PayPal Sandbox settlement in an isolated simulation runtime.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .network_matching import (
    DonorBranch,
    ReceivingBranch,
    BranchCandidateMatch,
    LogisticsCarrierOption,
    IncrementalNetworkEconomics,
    MultiBranchTransferPlan,
    match_candidate_receivers,
    match_candidate_donors,
    optimize_logistics_partners,
    calculate_incremental_network_value,
    solve_constrained_greedy_balancing,
)
from .buyer_matching import match_buyers, BuyerMatchResult
from ..office.service import office_service
from ..authorization.entities import build_user_entity

logger = logging.getLogger("simulation.orchestrator")

SIMULATION_STEPS = [
    "1. INVENTORY AUDIT",
    "2. NETWORK MATCHING",
    "3. STRATEGY & ECONOMICS",
    "4. LOGISTICS OPTIMIZATION",
    "5. TRANSFER / ORDER MANIFEST",
    "6. CEDAR AUTHORIZATION",
    "7. SETTLEMENT / PAYPAL",
    "8. FULFILLMENT & DISPATCH",
    "9. RECONCILIATION & CEO REPORT",
]


class SimulationState(BaseModel):
    simulation_run_id: str
    scenario_id: str  # "SCENARIO_A" | "SCENARIO_B" | "SCENARIO_C" | "SCENARIO_D"
    scenario_name: str
    scenario_description: str
    operating_perspective: str = "SURPLUS_DONOR"  # "SURPLUS_DONOR" | "STOCKOUT_RECEIVER" | "NETWORK_BALANCING" | "EXTERNAL_LIQUIDATION"
    sku_id: str
    source_store_id: str
    product_name: str
    status: str = "IDLE"  # IDLE, RUNNING, PAUSED, AWAITING_APPROVAL, AWAITING_PAYMENT, COMPLETED, REJECTED
    current_step_index: int = 0
    current_step_name: str = SIMULATION_STEPS[0]
    playback_speed: float = 1.0
    auto_approve: bool = False
    is_simulation: bool = True

    # Timeline & Events
    timeline: List[Dict[str, Any]] = []
    live_event_feed: List[Dict[str, Any]] = []

    # Network Perspectives & Data
    donor_branch: Optional[Dict[str, Any]] = None
    receiving_branch: Optional[Dict[str, Any]] = None
    candidate_branches: Optional[List[Dict[str, Any]]] = None
    logistics_comparison: Optional[List[Dict[str, Any]]] = None
    network_economics: Optional[Dict[str, Any]] = None
    network_balance_plan: Optional[Dict[str, Any]] = None

    # Stage Outputs
    inventory_discovery: Optional[Dict[str, Any]] = None
    buyer_discovery: Optional[Dict[str, Any]] = None
    recovery_analysis: Optional[Dict[str, Any]] = None
    recovery_planning: Optional[Dict[str, Any]] = None
    offer_creation: Optional[Dict[str, Any]] = None
    human_approval: Optional[Dict[str, Any]] = None
    paypal_checkout: Optional[Dict[str, Any]] = None
    fulfillment: Optional[Dict[str, Any]] = None
    financial_reconciliation: Optional[Dict[str, Any]] = None
    ceo_report: Optional[Dict[str, Any]] = None


class SimulationOrchestrator:
    """
    Manages active simulation lifecycle, network redistribution matching,
    logistics comparisons, and agent visualization choreography.
    """

    def __init__(self):
        self._active_simulations: Dict[str, SimulationState] = {}
        self._default_sim_id: str = "SIM-INIT-001"
        self._init_default_scenario("SCENARIO_A")

    def _init_default_scenario(self, scenario_type: str = "SCENARIO_A") -> SimulationState:
        run_id = f"SIM-{uuid.uuid4().hex[:6].upper()}"

        if scenario_type == "SCENARIO_B":
            # Scenario B: Stockout Prevention (Receiving Branch View)
            state = SimulationState(
                simulation_run_id=run_id,
                scenario_id="SCENARIO_B",
                scenario_name="Scenario B: Stockout Prevention (Receiving Branch)",
                scenario_description="Store D detects acute inventory shortage (8 units left, stockout in 6.0h). Discovers donor surplus at Store A, verifies safety stock preservation, selects SwiftReefer for 26-min ETA, and saves $360 vs emergency supplier replenishment.",
                operating_perspective="STOCKOUT_RECEIVER",
                sku_id="BER-003",
                source_store_id="STORE_D",
                product_name="Organic Blueberries 250g",
            )
        elif scenario_type == "SCENARIO_C":
            # Scenario C: Network-Wide Inventory Balancing
            state = SimulationState(
                simulation_run_id=run_id,
                scenario_id="SCENARIO_C",
                scenario_name="Scenario C: Network-Wide Inventory Balancing",
                scenario_description="Multi-branch network balancing across 4 branches. Solves simultaneous surpluses at Store A/C and acute shortages at Store B/D via deterministic constrained greedy matching, generating +$613 consolidated network value.",
                operating_perspective="NETWORK_BALANCING",
                sku_id="NET-MULTI",
                source_store_id="STORE_A",
                product_name="Multi-SKU Perishable Network (Yogurt & Salmon)",
            )
        elif scenario_type == "SCENARIO_D":
            # Scenario D: External B2B Liquidation Fallback
            state = SimulationState(
                simulation_run_id=run_id,
                scenario_id="SCENARIO_D",
                scenario_name="Scenario D: External B2B Liquidation Fallback",
                scenario_description="Internal store network cannot absorb inventory profitably (internal cold storage full, 36h expiry). Matches verified B2B buyers, structures commercial contract, obtains Cedar sign-off, and executes genuine PayPal Sandbox checkout.",
                operating_perspective="EXTERNAL_LIQUIDATION",
                sku_id="MILK-001",
                source_store_id="STORE_A",
                product_name="Pastured Whole Milk 1L",
            )
        else:
            # Scenario A: Surplus Inventory Rescue (Donor Branch View)
            state = SimulationState(
                simulation_run_id=run_id,
                scenario_id="SCENARIO_A",
                scenario_name="Scenario A: Surplus Inventory Rescue (Donor Branch)",
                scenario_description="Store A has 100 units surplus of perishable dairy facing 3-day expiry. Discovers high-demand Store B, verifies cold chain, proves internal transfer creates +$280 net network value over markdown, and executes inter-store dispatch.",
                operating_perspective="SURPLUS_DONOR",
                sku_id="YOG-001",
                source_store_id="STORE_A",
                product_name="Greek Yogurt 500g",
            )

        self._active_simulations[run_id] = state
        self._default_sim_id = run_id
        return state

    def get_current_simulation(self, run_id: Optional[str] = None) -> SimulationState:
        target_id = run_id or self._default_sim_id
        if target_id not in self._active_simulations:
            return self._init_default_scenario("SCENARIO_A")
        return self._active_simulations[target_id]

    def get_order_data(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Look up active simulation recovery order by order_id."""
        for sim in self._active_simulations.values():
            if sim.offer_creation and sim.offer_creation.get("order_id") == order_id:
                return {
                    "order_id": order_id,
                    "total_amount": float(sim.offer_creation.get("total_amount", 187.20)),
                    "currency": sim.offer_creation.get("currency", "USD"),
                    "status": "CREATED",
                    "sku_id": sim.sku_id,
                    "product_name": sim.product_name,
                    "quantity": sim.offer_creation.get("quantity", 104),
                }
        if order_id.startswith("SIM-") or "SIM" in order_id:
            return {
                "order_id": order_id,
                "total_amount": 187.20,
                "currency": "USD",
                "status": "CREATED",
                "sku_id": "YOG-001",
                "product_name": "Greek Yogurt 500g",
                "quantity": 104,
            }
        return None

    def _record_event(self, state: SimulationState, agent_name: str, event_type: str, details: str):
        now_str = time.strftime("%H:%M:%S")
        entry = {
            "timestamp": now_str,
            "agent": agent_name,
            "action": event_type,
            "details": details,
            "step": state.current_step_name,
        }
        state.timeline.append(entry)
        state.live_event_feed.insert(0, entry)
        if len(state.live_event_feed) > 50:
            state.live_event_feed.pop()

    async def reset_simulation(self, scenario_type: str = "SCENARIO_A") -> SimulationState:
        """Resets the simulation runtime with a designated scenario."""
        new_state = self._init_default_scenario(scenario_type)
        self._record_event(
            new_state,
            "Sarah Chen (CEO)",
            "SIMULATION_RESET",
            f"Initialized fresh isolated simulation run {new_state.simulation_run_id} ({scenario_type})",
        )
        try:
            await office_service.reset_all()
        except Exception as e:
            logger.warning(f"Error resetting office agents: {e}")
        return new_state

    async def execute_step(self, run_id: Optional[str] = None) -> SimulationState:
        """
        Advances the simulation by one discrete step in the 9-stage workflow.
        """
        state = self.get_current_simulation(run_id)
        idx = state.current_step_index

        if state.status in ("COMPLETED", "REJECTED"):
            return state

        # -------------------------------------------------------------
        # STAGE 1: INVENTORY AUDIT (Surplus & Shortage Detection)
        # -------------------------------------------------------------
        if idx == 0:
            state.status = "RUNNING"
            state.current_step_name = SIMULATION_STEPS[0]
            self._record_event(
                state,
                "Sarah Chen (CEO)",
                "TASK_ASSIGNED",
                f"Delegated inventory risk & balance audit for {state.sku_id} at {state.source_store_id} to Marcus Vance (Inventory).",
            )

            await office_service.send_speech_bubble(1, f"Marcus, audit perishable inventory risk for {state.sku_id} at {state.source_store_id}.", "instruction")
            await office_service.move_agent_to(2, "ceo_briefing")
            await office_service.set_agent_active(2, is_active=True)
            await office_service.move_agent_to(2, "workstation")
            await office_service.send_speech_bubble(2, "Auditing branch stock positions with RiskEngine...", "working")
            await office_service.start_tool(2, f"inv-audit-{int(time.time())}", "Auditing stock expiry and velocity", "RiskEngine")

            if state.scenario_id == "SCENARIO_B":
                # Stockout Prevention (Store D)
                state.receiving_branch = {
                    "store_id": "STORE_D",
                    "store_name": "East Branch (Store D)",
                    "sku_id": "BER-003",
                    "product_name": "Organic Blueberries 250g",
                    "current_stock": 8,
                    "target_stock": 60,
                    "shortage_quantity": 52,
                    "daily_demand": 32.0,
                    "stockout_deadline_hours": 6.0,
                    "storage_capacity": 100,
                    "available_capacity": 92,
                    "supports_cold_chain": True,
                }
                state.inventory_discovery = {
                    "sku_id": "BER-003",
                    "product_name": "Organic Blueberries 250g",
                    "store_id": "STORE_D",
                    "quantity": 8,
                    "days_to_expiry": 4.0,
                    "at_risk_quantity": 52,
                    "at_risk_value": 155.48,
                    "risk_score": 92,
                    "risk_level": "CRITICAL_SHORTAGE",
                }
                audit_msg = "Acute shortage detected: 8 units remaining at Store D. Projected stockout in 6.0 hours."
            elif state.scenario_id == "SCENARIO_C":
                # Network-Wide Balancing
                state.inventory_discovery = {
                    "sku_id": "NET-MULTI",
                    "product_name": "Multi-SKU Network Balancing",
                    "store_id": "NETWORK_WIDE",
                    "quantity": 380,
                    "days_to_expiry": 3.5,
                    "at_risk_quantity": 125,
                    "at_risk_value": 785.00,
                    "risk_score": 85,
                    "risk_level": "NETWORK_IMBALANCE",
                }
                audit_msg = "Network audit complete: 125 units imbalance across 4 branches (Store A/C surplus, Store B/D shortage)."
            elif state.scenario_id == "SCENARIO_D":
                # External Liquidation Fallback
                state.donor_branch = {
                    "store_id": "STORE_A",
                    "store_name": "Main Hub (Store A)",
                    "sku_id": "MILK-001",
                    "product_name": "Pastured Whole Milk 1L",
                    "current_stock": 135,
                    "safety_stock": 15,
                    "transferable_quantity": 120,
                    "daily_velocity": 5.0,
                    "days_to_expiry": 1.5,
                    "cost_price": 2.20,
                    "selling_price": 3.99,
                    "temperature_class": "REFRIGERATED",
                    "requires_cold_chain": True,
                }
                state.inventory_discovery = {
                    "sku_id": "MILK-001",
                    "product_name": "Pastured Whole Milk 1L",
                    "store_id": "STORE_A",
                    "quantity": 135,
                    "days_to_expiry": 1.5,
                    "at_risk_quantity": 120,
                    "at_risk_value": 478.80,
                    "risk_score": 94,
                    "risk_level": "CRITICAL_EXPIRY",
                }
                audit_msg = "Critical surplus: 120 units at Store A (36h expiry). Internal branches at 100% cold capacity."
            else:
                # Scenario A: Surplus Rescue (Store A)
                state.donor_branch = {
                    "store_id": "STORE_A",
                    "store_name": "Main Hub (Store A)",
                    "sku_id": "YOG-001",
                    "product_name": "Greek Yogurt 500g",
                    "current_stock": 120,
                    "safety_stock": 20,
                    "transferable_quantity": 100,
                    "daily_velocity": 4.0,
                    "days_to_expiry": 3.0,
                    "cost_price": 2.50,
                    "selling_price": 3.99,
                    "temperature_class": "REFRIGERATED",
                    "requires_cold_chain": True,
                }
                state.inventory_discovery = {
                    "sku_id": "YOG-001",
                    "product_name": "Greek Yogurt 500g",
                    "store_id": "STORE_A",
                    "quantity": 120,
                    "days_to_expiry": 3.0,
                    "at_risk_quantity": 100,
                    "at_risk_value": 399.00,
                    "risk_score": 88,
                    "risk_level": "CRITICAL_SURPLUS",
                }
                audit_msg = "Surplus audit complete: 100 units transferable above safety stock (20 units buffer preserved)."

            self._record_event(state, "Marcus Vance (Inventory)", "TASK_COMPLETED", audit_msg)
            await office_service.done_tool(2, f"inv-audit-{int(time.time())}")
            await office_service.move_agent_to(2, "ceo_reporting")
            await office_service.send_speech_bubble(2, audit_msg, "reporting")
            state.current_step_index = 1
            state.current_step_name = SIMULATION_STEPS[1]
            return state

        # -------------------------------------------------------------
        # STAGE 2: NETWORK MATCHING (Donor & Receiver Discovery)
        # -------------------------------------------------------------
        elif idx == 1:
            state.current_step_name = SIMULATION_STEPS[1]

            if state.scenario_id == "SCENARIO_D":
                # External B2B Buyer Matching for Scenario D
                self._record_event(state, "Sarah Chen (CEO)", "TASK_ASSIGNED", "Assigned external B2B commercial buyer scanning to Aisha Patel (Commerce).")
                await office_service.send_speech_bubble(1, "Aisha, scan verified B2B wholesale buyers with refrigerated capacity.", "instruction")
                await office_service.move_agent_to(5, "ceo_briefing")
                await office_service.set_agent_active(5, is_active=True)
                await office_service.move_agent_to(5, "workstation")
                await office_service.send_speech_bubble(5, "Scanning secondary commercial buyer registry...", "working")
                await office_service.start_tool(5, f"com-match-{int(time.time())}", "Querying B2B Buyer Matching Engine", "BuyerMatchingService")

                buyer_matches = match_buyers(
                    sku_id=state.sku_id,
                    product_name=state.product_name,
                    quantity=120,
                    unit_price=1.80,
                    requires_cold_chain=True,
                )
                top_buyer = buyer_matches[0].dict() if buyer_matches else None
                state.buyer_discovery = {
                    "total_candidates_evaluated": len(buyer_matches),
                    "compatible_candidates_count": len([b for b in buyer_matches if b.is_compatible]),
                    "top_matched_buyer": top_buyer,
                    "candidates": [b.dict() for b in buyer_matches],
                }
                match_summary = f"Matched top buyer: {top_buyer['name']} (Match: {top_buyer['match_score']}%, PayPal verified)."
                self._record_event(state, "Aisha Patel (Commerce)", "TASK_COMPLETED", match_summary)
                await office_service.done_tool(5, f"com-match-{int(time.time())}")
                await office_service.move_agent_to(5, "ceo_reporting")
                await office_service.send_speech_bubble(5, match_summary, "reporting")

            elif state.scenario_id == "SCENARIO_B":
                # Donor discovery for receiving store
                self._record_event(state, "Sarah Chen (CEO)", "TASK_ASSIGNED", "Assigned donor branch discovery to Elena Rostova (Strategy).")
                await office_service.send_speech_bubble(1, "Elena, scan store network for donor branches with transferable stock and safety buffer.", "instruction")
                await office_service.move_agent_to(3, "ceo_briefing")
                await office_service.set_agent_active(3, is_active=True)
                await office_service.move_agent_to(3, "workstation")
                await office_service.send_speech_bubble(3, "Scanning branch network for surplus donors...", "working")
                await office_service.start_tool(3, f"donor-match-{int(time.time())}", "Evaluating donor candidates", "NetworkMatchingEngine")

                receiver_obj = ReceivingBranch(
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
                donors_pool = [
                    DonorBranch(
                        store_id="STORE_A",
                        store_name="Main Hub (Store A)",
                        sku_id="BER-003",
                        product_name="Organic Blueberries 250g",
                        current_stock=75,
                        safety_stock=20,
                        transferable_quantity=55,
                        daily_velocity=3.0,
                        days_to_expiry=4.0,
                        cost_price=1.80,
                        selling_price=2.99,
                        temperature_class="REFRIGERATED",
                        requires_cold_chain=True,
                        latitude=34.0522,
                        longitude=-118.2437,
                    ),
                    DonorBranch(
                        store_id="STORE_C",
                        store_name="South Branch (Store C)",
                        sku_id="BER-003",
                        product_name="Organic Blueberries 250g",
                        current_stock=10,
                        safety_stock=15,
                        transferable_quantity=0,
                        daily_velocity=2.0,
                        days_to_expiry=4.0,
                        cost_price=1.80,
                        selling_price=2.99,
                        temperature_class="REFRIGERATED",
                        requires_cold_chain=False,
                        latitude=33.9525,
                        longitude=-118.2551,
                    ),
                ]
                donor_matches = match_candidate_donors(receiver_obj, donors_pool)
                state.candidate_branches = [m.dict() for m in donor_matches]
                top_donor = donor_matches[0]
                match_summary = f"Identified top donor: {top_donor.store_name} (55 transferable units, ETA 26 min, Match: {top_donor.match_score}%)."
                self._record_event(state, "Elena Rostova (Strategy)", "TASK_COMPLETED", match_summary)
                await office_service.done_tool(3, f"donor-match-{int(time.time())}")
                await office_service.move_agent_to(3, "ceo_reporting")
                await office_service.send_speech_bubble(3, match_summary, "reporting")

            elif state.scenario_id == "SCENARIO_C":
                # Network-Wide Balancing
                self._record_event(state, "Sarah Chen (CEO)", "TASK_ASSIGNED", "Assigned multi-branch rebalancing optimization to Elena Rostova (Strategy).")
                await office_service.send_speech_bubble(1, "Elena, compute deterministic constrained greedy balancing across all 4 branches.", "instruction")
                await office_service.move_agent_to(3, "ceo_briefing")
                await office_service.set_agent_active(3, is_active=True)
                await office_service.move_agent_to(3, "workstation")
                await office_service.send_speech_bubble(3, "Running constrained greedy network solver...", "working")
                await office_service.start_tool(3, f"net-balance-{int(time.time())}", "Solving multi-branch pairing matrix", "NetworkMatchingEngine")

                donors_pool = [
                    DonorBranch(
                        store_id="STORE_A",
                        store_name="Main Hub",
                        sku_id="YOG-001",
                        product_name="Greek Yogurt 500g",
                        current_stock=100,
                        safety_stock=20,
                        transferable_quantity=80,
                        daily_velocity=4.0,
                        days_to_expiry=3.5,
                        cost_price=2.50,
                        selling_price=3.99,
                        temperature_class="REFRIGERATED",
                        requires_cold_chain=True,
                        latitude=34.0522,
                        longitude=-118.2437,
                    ),
                    DonorBranch(
                        store_id="STORE_C",
                        store_name="South Branch",
                        sku_id="SAL-002",
                        product_name="Atlantic Salmon Fillet",
                        current_stock=60,
                        safety_stock=15,
                        transferable_quantity=45,
                        daily_velocity=2.0,
                        days_to_expiry=4.0,
                        cost_price=8.50,
                        selling_price=12.99,
                        temperature_class="REFRIGERATED",
                        requires_cold_chain=True,
                        latitude=33.9525,
                        longitude=-118.2551,
                    ),
                ]
                receivers_pool = [
                    ReceivingBranch(
                        store_id="STORE_B",
                        store_name="North Branch",
                        sku_id="YOG-001",
                        product_name="Greek Yogurt 500g",
                        current_stock=10,
                        target_stock=80,
                        daily_demand=25.0,
                        shortage_quantity=70,
                        storage_capacity=150,
                        available_capacity=140,
                        absorbable_quantity=75,
                        stockout_deadline_hours=12.0,
                        supports_cold_chain=True,
                        latitude=34.1425,
                        longitude=-118.2551,
                    ),
                    ReceivingBranch(
                        store_id="STORE_D",
                        store_name="East Branch",
                        sku_id="SAL-002",
                        product_name="Atlantic Salmon Fillet",
                        current_stock=5,
                        target_stock=45,
                        daily_demand=18.0,
                        shortage_quantity=40,
                        storage_capacity=100,
                        available_capacity=95,
                        absorbable_quantity=45,
                        stockout_deadline_hours=8.0,
                        supports_cold_chain=True,
                        latitude=34.0522,
                        longitude=-118.1437,
                    ),
                ]
                balance_plan = solve_constrained_greedy_balancing(donors_pool, receivers_pool)
                state.network_balance_plan = balance_plan.dict()
                match_summary = f"Balancing plan computed: 2 optimal routes scheduled, 110 units reallocated, +${balance_plan.total_net_network_value:.2f} value."
                self._record_event(state, "Elena Rostova (Strategy)", "TASK_COMPLETED", match_summary)
                await office_service.done_tool(3, f"net-balance-{int(time.time())}")
                await office_service.move_agent_to(3, "ceo_reporting")
                await office_service.send_speech_bubble(3, match_summary, "reporting")

            else:
                # Scenario A: Receiving branch discovery for surplus donor
                self._record_event(state, "Sarah Chen (CEO)", "TASK_ASSIGNED", "Assigned receiving branch candidate discovery to Elena Rostova (Strategy).")
                await office_service.send_speech_bubble(1, "Elena, scan store network for receiving branches capable of absorbing surplus dairy.", "instruction")
                await office_service.move_agent_to(3, "ceo_briefing")
                await office_service.set_agent_active(3, is_active=True)
                await office_service.move_agent_to(3, "workstation")
                await office_service.send_speech_bubble(3, "Scanning receiving branches and cold storage capacity...", "working")
                await office_service.start_tool(3, f"rcv-match-{int(time.time())}", "Evaluating receiving branches", "NetworkMatchingEngine")

                donor_obj = DonorBranch(
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
                receivers_pool = [
                    ReceivingBranch(
                        store_id="STORE_B",
                        store_name="North Branch (Store B)",
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
                    ),
                    ReceivingBranch(
                        store_id="STORE_C",
                        store_name="South Branch (Store C)",
                        sku_id="YOG-001",
                        product_name="Greek Yogurt 500g",
                        current_stock=15,
                        target_stock=50,
                        daily_demand=8.0,
                        shortage_quantity=35,
                        storage_capacity=80,
                        available_capacity=65,
                        absorbable_quantity=24,
                        stockout_deadline_hours=24.0,
                        supports_cold_chain=False,
                        latitude=33.9525,
                        longitude=-118.2551,
                    ),
                    ReceivingBranch(
                        store_id="STORE_D",
                        store_name="East Branch (Store D)",
                        sku_id="YOG-001",
                        product_name="Greek Yogurt 500g",
                        current_stock=90,
                        target_stock=90,
                        daily_demand=5.0,
                        shortage_quantity=0,
                        storage_capacity=100,
                        available_capacity=0,
                        absorbable_quantity=0,
                        stockout_deadline_hours=72.0,
                        supports_cold_chain=True,
                        latitude=34.0522,
                        longitude=-118.1437,
                    ),
                ]
                receiver_matches = match_candidate_receivers(donor_obj, receivers_pool)
                state.candidate_branches = [m.dict() for m in receiver_matches]
                top_match = receiver_matches[0]
                match_summary = f"Top candidate matched: {top_match.store_name} (Match: {top_match.match_score}%, absorb 90 units, +${top_match.net_economic_value:.2f} value)."
                self._record_event(state, "Elena Rostova (Strategy)", "TASK_COMPLETED", match_summary)
                await office_service.done_tool(3, f"rcv-match-{int(time.time())}")
                await office_service.move_agent_to(3, "ceo_reporting")
                await office_service.send_speech_bubble(3, match_summary, "reporting")

            state.current_step_index = 2
            state.current_step_name = SIMULATION_STEPS[2]
            return state

        # -------------------------------------------------------------
        # STAGE 3: STRATEGY & ECONOMICS (Incremental Network Value)
        # -------------------------------------------------------------
        elif idx == 2:
            state.current_step_name = SIMULATION_STEPS[2]
            self._record_event(state, "Sarah Chen (CEO)", "TASK_ASSIGNED", "Assigned incremental network economics and trade-off evaluation to Elena Rostova (Strategy).")
            await office_service.send_speech_bubble(1, "Elena, evaluate incremental network value against markdown, supplier rush, and liquidation.", "instruction")
            await office_service.move_agent_to(3, "ceo_briefing")
            await office_service.set_agent_active(3, is_active=True)
            await office_service.move_agent_to(3, "workstation")
            await office_service.send_speech_bubble(3, "Calculating net network economic delta...", "working")
            await office_service.start_tool(3, f"econ-eval-{int(time.time())}", "Computing incremental network economics", "DecisionEngine")

            if state.scenario_id == "SCENARIO_B":
                # Stockout Prevention Economics
                selected_action = "INTERNAL_TRANSFER"
                net_val = 245.50
                reasoning = (
                    "Internal transfer from Store A protects $174.50 contribution margin and avoids $120.00 supplier rush penalty. "
                    "Creates $360.50 superior net network benefit compared to 24h supplier replenishment."
                )
                evaluated_actions = [
                    {"action": "INTERNAL_TRANSFER", "expected_net_recovery": 245.50, "economically_viable": True, "destination_store": "STORE_D"},
                    {"action": "SUPPLIER_REPLENISHMENT", "expected_net_recovery": -115.00, "economically_viable": False, "reason": "24h lead time causes 18h dead stockout"},
                    {"action": "NO_ACTION", "expected_net_recovery": -160.00, "economically_viable": False, "reason": "Full stockout and lost customer goodwill"},
                ]
                state.network_economics = {
                    "transfer_quantity": 50,
                    "retail_price": 2.99,
                    "cost_price": 1.80,
                    "margin_protected_at_receiver": 59.50,
                    "avoided_markdown_writeoff_loss": 76.50,
                    "gross_revenue_protected": 149.50,
                    "transport_cost": 49.32,
                    "handling_cost": 7.50,
                    "transit_spoilage_risk_cost": 1.35,
                    "donor_opportunity_cost": 0.0,
                    "net_incremental_network_value": 245.50,
                    "supplier_replenishment_comparison": {
                        "supplier_lead_time_hours": 24.0,
                        "supplier_emergency_surcharge": 85.00,
                        "lost_sales_before_supplier_arrival": 145.00,
                        "supplier_net_penalty": 230.00,
                        "internal_transfer_advantage": 360.50,
                        "economic_conclusion": "Internal transfer creates $360.50 USD superior net network value over emergency supplier re-ordering.",
                    },
                    "alternative_actions_ranking": evaluated_actions,
                }

            elif state.scenario_id == "SCENARIO_C":
                # Network-Wide Balancing Economics
                selected_action = "NETWORK_BALANCING"
                net_val = 613.60
                reasoning = "Multi-branch rebalancing reallocates 110 units across 2 corridors, protecting $395 margin and avoiding $340 write-off losses (-$121.40 freight)."
                evaluated_actions = [
                    {"action": "NETWORK_BALANCING", "expected_net_recovery": 613.60, "economically_viable": True},
                    {"action": "ISOLATED_MARKDOWNS", "expected_net_recovery": 185.00, "economically_viable": True, "reason": "Forces heavy 40% local discounts"},
                    {"action": "NO_ACTION", "expected_net_recovery": -420.00, "economically_viable": False, "reason": "Mass spoilage at donors and stockouts at receivers"},
                ]
                state.network_economics = {
                    "transfer_quantity": 110,
                    "total_margin_protected": 395.00,
                    "total_avoided_spoilage": 340.00,
                    "total_freight_cost": 121.40,
                    "net_incremental_network_value": 613.60,
                    "alternative_actions_ranking": evaluated_actions,
                }

            elif state.scenario_id == "SCENARIO_D":
                # External B2B Liquidation Fallback Economics
                selected_action = "EXTERNAL_LIQUIDATION"
                net_val = 182.00
                reasoning = "Internal branch cold-storage is at 100% capacity. Commercial B2B liquidation to Metro Retail recovers $182.00 net vs -$42.00 disposal fee."
                evaluated_actions = [
                    {"action": "EXTERNAL_LIQUIDATION", "expected_net_recovery": 182.00, "economically_viable": True, "buyer": "Metro Retail Discount Mart"},
                    {"action": "INTERNAL_TRANSFER", "expected_net_recovery": 0.0, "economically_viable": False, "reason": "All internal store cold facilities full"},
                    {"action": "LOCAL_DISPOSAL", "expected_net_recovery": -42.00, "economically_viable": False, "reason": "Hazardous bio-waste disposal charge"},
                ]
                state.network_economics = {
                    "transfer_quantity": 120,
                    "gross_recovery": 216.00,
                    "logistics_and_buyer_discount": 34.00,
                    "net_incremental_network_value": 182.00,
                    "alternative_actions_ranking": evaluated_actions,
                }

            else:
                # Scenario A: Surplus Rescue Economics
                selected_action = "INTERNAL_TRANSFER"
                net_val = 280.28
                reasoning = (
                    "Transfer to Store B protects $134.10 retail margin and avoids $208.25 spoilage write-off. "
                    "Net network value +$280.28 vs $109.35 local markdown (+170.93 margin advantage)."
                )
                evaluated_actions = [
                    {"action": "INTERNAL_TRANSFER", "expected_net_recovery": 280.28, "economically_viable": True, "destination_store": "STORE_B"},
                    {"action": "LOCAL_MARKDOWN", "expected_net_recovery": 109.35, "economically_viable": True, "reason": "Requires 35% discount with only 65% sell-through"},
                    {"action": "PRODUCT_BUNDLE", "expected_net_recovery": 85.00, "economically_viable": True},
                    {"action": "SUPPLIER_RETURN", "expected_net_recovery": 65.00, "economically_viable": True, "reason": "50% restocking penalty + return freight"},
                    {"action": "DISPOSAL", "expected_net_recovery": -35.00, "economically_viable": False, "reason": "Hazardous waste handling fee"},
                ]
                state.network_economics = {
                    "transfer_quantity": 90,
                    "retail_price": 3.99,
                    "cost_price": 2.50,
                    "margin_protected_at_receiver": 134.10,
                    "avoided_markdown_writeoff_loss": 208.25,
                    "gross_revenue_protected": 359.10,
                    "transport_cost": 45.19,
                    "handling_cost": 13.50,
                    "transit_spoilage_risk_cost": 3.38,
                    "donor_opportunity_cost": 0.0,
                    "net_incremental_network_value": 280.28,
                    "supplier_replenishment_comparison": {
                        "supplier_lead_time_hours": 24.0,
                        "supplier_emergency_surcharge": 85.00,
                        "lost_sales_before_supplier_arrival": 95.00,
                        "supplier_net_penalty": 180.00,
                        "internal_transfer_advantage": 460.28,
                        "economic_conclusion": "Internal transfer generates $460.28 superior consolidated return over supplier re-order.",
                    },
                    "alternative_actions_ranking": evaluated_actions,
                }

            state.recovery_analysis = {
                "selected_action": selected_action,
                "expected_net_recovery": net_val,
                "reasoning": reasoning,
                "evaluated_actions": evaluated_actions,
            }

            self._record_event(state, "Elena Rostova (Strategy)", "TASK_COMPLETED", f"Strategic recommendation: {selected_action} (+${net_val:.2f} net value).")
            await office_service.done_tool(3, f"econ-eval-{int(time.time())}")
            await office_service.move_agent_to(3, "ceo_reporting")
            await office_service.send_speech_bubble(3, f"Recommended {selected_action}: Net value +${net_val:.2f}", "reporting")
            state.current_step_index = 3
            state.current_step_name = SIMULATION_STEPS[3]
            return state

        # -------------------------------------------------------------
        # STAGE 4: LOGISTICS OPTIMIZATION (Carrier Comparison)
        # -------------------------------------------------------------
        elif idx == 3:
            state.current_step_name = SIMULATION_STEPS[3]

            # Multi-agent collaboration in Conference Room between Elena (Strategy) and David Kim (Logistics)
            await office_service.move_agent_to(3, "conference")
            await office_service.move_agent_to(4, "conference")
            await office_service.send_speech_bubble(3, "David, optimize carrier fleet for road distance, ETA, and cold-chain constraints.", "working")
            await office_service.send_speech_bubble(4, "Evaluating road network routes and carrier suitability...", "reporting")

            self._record_event(state, "Sarah Chen (CEO)", "TASK_ASSIGNED", "Assigned road-network freight partner optimization to David Kim (Logistics).")
            await office_service.move_agent_to(4, "workstation")
            await office_service.set_agent_active(4, is_active=True)
            await office_service.start_tool(4, f"log-opt-{int(time.time())}", "Optimizing road logistics partners", "LogisticsEngine")

            # Evaluate carriers
            if state.scenario_id == "SCENARIO_B":
                src_lat, src_lon = 34.0522, -118.2437  # Store A
                dst_lat, dst_lon = 34.0522, -118.1437  # Store D
                qty = 50
                cold = True
                hours_exp = 96.0
            elif state.scenario_id == "SCENARIO_D":
                src_lat, src_lon = 34.0522, -118.2437  # Store A
                dst_lat, dst_lon = 34.1022, -118.1937  # Metro Buyer Logistics Zone
                qty = 120
                cold = True
                hours_exp = 36.0
            else:
                src_lat, src_lon = 34.0522, -118.2437  # Store A
                dst_lat, dst_lon = 34.1425, -118.2551  # Store B
                qty = 90
                cold = True
                hours_exp = 72.0

            carrier_options, best_carrier = optimize_logistics_partners(src_lat, src_lon, dst_lat, dst_lon, qty, cold, hours_exp)
            state.logistics_comparison = [c.dict() for c in carrier_options]

            selected_carrier_name = best_carrier.partner_name if best_carrier else "SwiftReefer Express"
            transit_min = best_carrier.estimated_journey_time_minutes if best_carrier else 25
            freight_amt = best_carrier.transport_cost if best_carrier else 45.19
            road_km = best_carrier.road_distance_km if best_carrier else 12.6

            state.recovery_planning = {
                "type": "INTER_STORE_TRANSFER" if state.scenario_id != "SCENARIO_D" else "COMMERCIAL_LIQUIDATION",
                "source_store_id": state.source_store_id,
                "target_store_id": "STORE_B" if state.scenario_id == "SCENARIO_A" else ("STORE_D" if state.scenario_id == "SCENARIO_B" else "METRO_MART"),
                "quantity": qty,
                "selected_carrier": selected_carrier_name,
                "road_distance_km": road_km,
                "transit_minutes": transit_min,
                "freight_cost": freight_amt,
                "cold_chain_verified": True,
            }

            log_summary = f"Selected {selected_carrier_name} ({road_km} km road, {transit_min} min ETA, ${freight_amt:.2f} freight, Active Reefer)."
            self._record_event(state, "David Kim (Logistics)", "TASK_COMPLETED", log_summary)
            await office_service.done_tool(4, f"log-opt-{int(time.time())}")
            await office_service.move_agent_to(4, "ceo_reporting")
            await office_service.send_speech_bubble(4, log_summary, "reporting")

            state.current_step_index = 4
            state.current_step_name = SIMULATION_STEPS[4]
            return state

        # -------------------------------------------------------------
        # STAGE 5: TRANSFER / ORDER MANIFEST
        # -------------------------------------------------------------
        elif idx == 4:
            state.current_step_name = SIMULATION_STEPS[4]

            if state.scenario_id == "SCENARIO_D":
                # External commercial order for Scenario D
                order_id = f"SIM-ORD-EXT-{uuid.uuid4().hex[:5].upper()}"
                state.offer_creation = {
                    "type": "RECOVERY_ORDER",
                    "order_id": order_id,
                    "sku_id": state.sku_id,
                    "product_name": state.product_name,
                    "buyer_name": "Metro Retail Discount Mart",
                    "buyer_email": "procurement@metroretail.example.com",
                    "quantity": 120,
                    "unit_price": 1.80,
                    "total_amount": 216.00,
                    "currency": "USD",
                    "status": "CREATED",
                    "fulfillment_status": "UNFULFILLED",
                }
                manifest_msg = f"Issued formal B2B Recovery Order {order_id}: $216.00 USD for Metro Retail Mart."
                self._record_event(state, "Aisha Patel (Commerce)", "ORDER_CREATED", manifest_msg)
                await office_service.send_speech_bubble(5, manifest_msg, "reporting")
            else:
                # Internal transfer manifest for Scenarios A, B, C
                transfer_id = f"TR-MANIFEST-{uuid.uuid4().hex[:5].upper()}"
                plan = state.recovery_planning or {}
                state.offer_creation = {
                    "type": "TRANSFER_MANIFEST",
                    "transfer_id": transfer_id,
                    "source_store_id": plan.get("source_store_id", "STORE_A"),
                    "destination_store_id": plan.get("target_store_id", "STORE_B"),
                    "sku_id": state.sku_id,
                    "product_name": state.product_name,
                    "quantity": plan.get("quantity", 90),
                    "carrier": plan.get("selected_carrier", "SwiftReefer Express"),
                    "freight_cost": plan.get("freight_cost", 45.19),
                    "status": "MANIFEST_STAGED",
                }
                manifest_msg = f"Generated Transfer Manifest {transfer_id} ({plan.get('quantity', 90)} units staged at dock bay)."
                self._record_event(state, "David Kim (Logistics)", "MANIFEST_CREATED", manifest_msg)
                await office_service.send_speech_bubble(4, manifest_msg, "reporting")

            state.current_step_index = 5
            state.current_step_name = SIMULATION_STEPS[5]
            return state

        # -------------------------------------------------------------
        # STAGE 6: CEDAR AUTHORIZATION (Policy Gate)
        # -------------------------------------------------------------
        elif idx == 5:
            state.current_step_name = SIMULATION_STEPS[5]
            self._record_event(state, "Sarah Chen (CEO)", "POLICY_EVALUATION", "Evaluating Cedar RBAC & Risk Threshold authorization policies.")

            approval_id = f"APP-SIM-{uuid.uuid4().hex[:6].upper()}"
            threshold_desc = (
                "Inter-Branch Stock Redistribution Governance"
                if state.scenario_id != "SCENARIO_D"
                else "High-Value Secondary B2B Markdown Approval (> $150)"
            )

            if not state.auto_approve:
                state.status = "AWAITING_APPROVAL"
                state.human_approval = {
                    "approval_id": approval_id,
                    "status": "PENDING_DECISION",
                    "threshold_evaluated": threshold_desc,
                    "cedar_allowed": True,
                    "approver_role": "MANAGER",
                }
                waiting_agent = 5 if state.scenario_id == "SCENARIO_D" else 4
                await office_service.move_agent_to(waiting_agent, "approval")
                await office_service.set_permission(waiting_agent, required=True)
                await office_service.send_speech_bubble(waiting_agent, "Cedar policy triggered. Waiting in Approval Room for manager sign-off.", "approval", 4.5)
                self._record_event(state, "Sarah Chen (CEO)", "APPROVAL_REQUIRED", f"Cedar policy triggered: Operational sign-off required ({approval_id}).")
                return state
            else:
                state.human_approval = {
                    "approval_id": approval_id,
                    "status": "AUTO_APPROVED",
                    "threshold_evaluated": "Auto-Approve Active",
                    "cedar_allowed": True,
                    "approver_role": "AUTOMATED_POLICY",
                }
                self._record_event(state, "Sarah Chen (CEO)", "MANAGER_APPROVED", f"Cedar policy approved: Execution granted for {approval_id}.")
                state.current_step_index = 6
                state.current_step_name = SIMULATION_STEPS[6]
                return state

        # -------------------------------------------------------------
        # STAGE 7: SETTLEMENT / PAYPAL CHECKOUT
        # -------------------------------------------------------------
        elif idx == 6:
            state.current_step_name = SIMULATION_STEPS[6]

            if state.scenario_id != "SCENARIO_D":
                # Internal Redistribution: PayPal NOT APPLICABLE
                state.paypal_checkout = {
                    "status": "NOT_APPLICABLE",
                    "details": "Internal multi-branch inventory redistribution. Settled via enterprise inter-store inventory clearing ledger with zero payment processing fees.",
                }
                self._record_event(
                    state,
                    "Linda Zhang (Finance)",
                    "SETTLEMENT_INFO",
                    "Internal branch redistribution: Bypassing external payment checkout (cleared via inter-store ledger).",
                )
                state.current_step_index = 7
                state.current_step_name = SIMULATION_STEPS[7]
                return state

            # Scenario D: Genuine PayPal Sandbox Checkout
            order_data = state.offer_creation or {}
            order_id = order_data.get("order_id", "SIM-ORD-EXT-01")
            total_amt = order_data.get("total_amount", 216.00)

            if state.paypal_checkout and state.paypal_checkout.get("status") == "CAPTURED":
                self._record_event(
                    state,
                    "Linda Zhang (Finance)",
                    "PAYMENT_CONFIRMED",
                    f"Verified PayPal Capture: {state.paypal_checkout.get('paypal_capture_id')} (${total_amt:.2f} USD).",
                )
                state.current_step_index = 7
                state.current_step_name = SIMULATION_STEPS[7]
                return state

            state.status = "AWAITING_PAYMENT"
            state.paypal_checkout = {
                "status": "AWAITING_BUYER_APPROVAL",
                "recovery_order_id": order_id,
                "amount": total_amt,
                "currency": "USD",
                "buyer_name": "Metro Retail Discount Mart",
            }
            await office_service.send_speech_bubble(5, f"Recovery Order {order_id} generated. Awaiting buyer PayPal settlement.", "instruction", 4.5)
            self._record_event(
                state,
                "Linda Zhang (Finance)",
                "CHECKOUT_READY",
                f"PayPal Sandbox invoice ready for Metro Retail Discount Mart (${total_amt:.2f} USD). Click Pay via PayPal.",
            )
            return state

        # -------------------------------------------------------------
        # STAGE 8: FULFILLMENT & DISPATCH
        # -------------------------------------------------------------
        elif idx == 7:
            state.current_step_name = SIMULATION_STEPS[7]

            if state.scenario_id == "SCENARIO_D":
                # Strict State Gate: Do not fulfill if payment has not been verified and captured!
                if not state.paypal_checkout or state.paypal_checkout.get("status") != "CAPTURED":
                    self._record_event(
                        state,
                        "Tom Becker (Fulfillment)",
                        "PAYMENT_CAPTURE_FAILED",
                        "Fulfillment halted: Cannot release warehouse inventory without verified PayPal payment capture.",
                    )
                    state.status = "AWAITING_PAYMENT"
                    return state

                await office_service.move_agent_to(6, "workstation")
                await office_service.set_agent_active(6, is_active=True)
                await office_service.send_speech_bubble(6, "Payment capture verified. Releasing inventory for warehouse dispatch.", "working")

                order_data = state.offer_creation or {}
                state.fulfillment = {
                    "status": "FULFILLED",
                    "order_id": order_data.get("order_id"),
                    "released_inventory_units": 120,
                    "buyer_pickup_code": f"PKUP-{uuid.uuid4().hex[:6].upper()}",
                    "pallet_staged_zone": "Dock Bay 2",
                }
                fulfill_msg = "Inventory released: 120 units staged at Dock Bay 2 for Metro Retail commercial pickup."
            else:
                await office_service.move_agent_to(6, "workstation")
                await office_service.set_agent_active(6, is_active=True)
                await office_service.send_speech_bubble(6, "Authorization confirmed. Releasing inventory for warehouse dispatch.", "working")

                manifest = state.offer_creation or {}
                state.fulfillment = {
                    "status": "IN_TRANSIT",
                    "transfer_id": manifest.get("transfer_id"),
                    "carrier": manifest.get("carrier", "SwiftReefer Express"),
                    "tracking_number": f"TRK-SR-{uuid.uuid4().hex[:8].upper()}",
                    "eta_minutes": 22,
                    "temperature_logged_celsius": 3.8,
                }
                fulfill_msg = f"Dispatched: Carrier SwiftReefer has picked up transfer {manifest.get('transfer_id')}. Active cold chain maintained at 3.8°C."

            self._record_event(state, "Tom Becker (Fulfillment)", "FULFILLMENT_ACTIVE", fulfill_msg)
            await office_service.move_agent_to(6, "ceo_reporting")
            await office_service.send_speech_bubble(6, fulfill_msg, "reporting")
            state.current_step_index = 8
            state.current_step_name = SIMULATION_STEPS[8]
            return state

        # -------------------------------------------------------------
        # STAGE 9: RECONCILIATION & CEO REPORT
        # -------------------------------------------------------------
        elif idx == 8:
            state.current_step_name = SIMULATION_STEPS[8]
            self._record_event(state, "Linda Zhang (Finance)", "RECONCILING", "Auditing network ledger, freight settlement, and net economic value.")

            await office_service.move_agent_to(1, "conference")
            await office_service.move_agent_to(7, "conference")

            if state.scenario_id == "SCENARIO_B":
                gross_val = 149.50
                freight_deducted = 49.32
                net_val = 245.50
                notes = "Stockout avoided. Protected $174.50 contribution margin; saved $360.50 vs emergency supplier re-ordering."
            elif state.scenario_id == "SCENARIO_C":
                gross_val = 735.00
                freight_deducted = 121.40
                net_val = 613.60
                notes = "Network-wide rebalancing complete across 4 stores. 110 units reallocated, generating +$613.60 consolidated value."
            elif state.scenario_id == "SCENARIO_D":
                checkout = state.paypal_checkout or {}
                gross_val = float(checkout.get("amount", 216.00))
                paypal_fee = float(checkout.get("fee_amount", round(gross_val * 0.0349 + 0.49, 2)))
                freight_deducted = paypal_fee
                net_val = float(checkout.get("net_amount", round(gross_val - paypal_fee, 2)))
                payment_id = checkout.get("payment_id", "PAY-SIM-DEMO")
                capture_id = checkout.get("paypal_capture_id", "SIM-CAP-DEMO")
                notes = f"PayPal Sandbox Orders API v2 capture verified. Payment ID: {payment_id}. Capture ID: {capture_id}. Gross: ${gross_val:.2f} USD. PayPal Fee: ${paypal_fee:.2f}. Net: ${net_val:.2f} USD."
                if state.paypal_checkout:
                    state.paypal_checkout["reconciliation_status"] = "RECONCILED"
            else:
                gross_val = 359.10
                freight_deducted = 45.19
                net_val = 280.28
                notes = "Surplus transfer complete. Protected $134.10 margin at Store B; saved $170.93 vs local markdown."

            if state.scenario_id == "SCENARIO_D" and state.paypal_checkout:
                payment_id = state.paypal_checkout.get("payment_id", "PAY-SIM-DEMO")
                self._record_event(
                    state,
                    "Linda Zhang (Finance)",
                    "PAYMENT_RECONCILED",
                    f"Finance reconciled payment {payment_id}: Gross ${gross_val:.2f}, Fee ${freight_deducted:.2f}, Net ${net_val:.2f} deposited to company treasury.",
                )

            state.financial_reconciliation = {
                "status": "RECONCILED",
                "gross_recovered": gross_val,
                "fees_and_costs": freight_deducted,
                "net_recovery": net_val,
                "waste_avoided_percentage": 100.0,
                "audit_notes": notes,
            }

            state.ceo_report = {
                "report_id": f"CEO-REP-{uuid.uuid4().hex[:6].upper()}",
                "executive_summary": f"Autonomous Operations Complete: {state.scenario_name}. Net network value: ${net_val:.2f} USD.",
                "action_executed": state.recovery_analysis.get("selected_action") if state.recovery_analysis else "INTERNAL_TRANSFER",
                "governance_status": "APPROVED",
                "recommended_operational_change": "Maintain automated 3-day buffer transfer triggers for all perishable multi-branch corridors.",
            }

            self._record_event(state, "Sarah Chen (CEO)", "MISSION_ACCOMPLISHED", f"CEO Executive Report published. Mission completed successfully with +${net_val:.2f} network outcome.")
            await office_service.send_speech_bubble(7, f"Audit reconciled: Net network gain +${net_val:.2f}. Ledger updated.", "reporting")
            await office_service.send_speech_bubble(1, "Executive review complete: Autonomous network redistribution successful.", "success", 4.5)
            state.status = "COMPLETED"
            return state

        return state

    async def approve_pending_decision(self, run_id: Optional[str] = None, decision: str = "APPROVED") -> SimulationState:
        """Resumes simulation after manager approval decision."""
        state = self.get_current_simulation(run_id)
        if state.status != "AWAITING_APPROVAL":
            return state

        if decision.upper() == "APPROVED":
            state.human_approval["status"] = "MANAGER_APPROVED"
            state.status = "RUNNING"
            self._record_event(state, "Sarah Chen (CEO)", "MANAGER_APPROVED", f"Human manager approved operational request {state.human_approval.get('approval_id')}. Resuming workflow.")
            waiting_agent = 5 if state.scenario_id == "SCENARIO_D" else 4
            await office_service.set_permission(waiting_agent, required=False)
            await office_service.send_speech_bubble(1, f"Manager approved request {state.human_approval.get('approval_id')}. Resuming workflow.", "instruction", 4.0)
            await office_service.move_agent_to(waiting_agent, "workstation")
            state.current_step_index = 6
            state.current_step_name = SIMULATION_STEPS[6]
            return await self.execute_step(run_id)
        else:
            state.human_approval["status"] = "MANAGER_REJECTED"
            state.status = "REJECTED"
            self._record_event(state, "Sarah Chen (CEO)", "MANAGER_REJECTED", f"Manager rejected request {state.human_approval.get('approval_id')}. Workflow halted safely.")
            waiting_agent = 5 if state.scenario_id == "SCENARIO_D" else 4
            await office_service.set_permission(waiting_agent, required=False)
            await office_service.send_speech_bubble(1, "Manager rejected request. Workflow halted safely.", "failure", 4.5)
            return state

    async def confirm_paypal_capture(
        self,
        run_id: Optional[str],
        paypal_order_id: str,
        paypal_capture_id: str,
        amount: float,
        currency: str = "USD",
        payment_id: Optional[str] = None,
        fee_amount: float = 0.0,
        net_amount: Optional[float] = None,
        payer_id: Optional[str] = None,
        payer_email: Optional[str] = None,
        payer_name: Optional[str] = None,
    ) -> SimulationState:
        """Records confirmed PayPal payment capture and advances workflow."""
        state = self.get_current_simulation(run_id)

        # Resolve internal payment_id if not explicitly provided
        if not payment_id:
            from ..payments.service import payment_service
            sim_txn = payment_service._simulation_transactions.get(paypal_order_id)
            if sim_txn and sim_txn.get("payment_id"):
                payment_id = sim_txn["payment_id"]
            else:
                payment_id = f"PAY-SIM-{uuid.uuid4().hex[:8].upper()}"

        calculated_net = net_amount if net_amount is not None else round(amount - fee_amount, 2)
        buyer_details = {
            "payer_id": payer_id,
            "payer_email": payer_email,
            "payer_name": payer_name,
        }

        # Idempotency check: if already captured with the same capture_id, return without re-emitting duplicate events
        is_already_captured = (
            state.paypal_checkout
            and state.paypal_checkout.get("status") == "CAPTURED"
            and state.paypal_checkout.get("paypal_capture_id") == paypal_capture_id
        )

        state.paypal_checkout = {
            "status": "CAPTURED",
            "payment_id": payment_id,
            "paypal_order_id": paypal_order_id,
            "paypal_capture_id": paypal_capture_id,
            "capture_id": paypal_capture_id,
            "recovery_order_id": state.offer_creation.get("order_id") if state.offer_creation else "SIM-ORD-EXT-01",
            "amount": amount,
            "currency": currency,
            "fee_amount": fee_amount,
            "net_amount": calculated_net,
            "payer_id": payer_id,
            "payer_email": payer_email,
            "payer_name": payer_name,
            "buyer_details": buyer_details,
            "captured_at": state.paypal_checkout.get("captured_at") if is_already_captured else datetime.utcnow().isoformat(),
            "is_live_sandbox": True,
            "capture_status": "COMPLETED",
            "payment_status": "CAPTURED",
            "reconciliation_status": "PENDING",
        }

        if not is_already_captured:
            # Emit standard progression events
            self._record_event(
                state,
                "Aisha Patel (Commerce)",
                "PAYMENT_APPROVAL_RECEIVED",
                f"Buyer approved order {paypal_order_id} in PayPal checkout.",
            )
            self._record_event(
                state,
                "Linda Zhang (Finance)",
                "PAYMENT_CAPTURE_STARTED",
                f"Initiating PayPal Orders v2 capture for {paypal_order_id}...",
            )
            self._record_event(
                state,
                "Linda Zhang (Finance)",
                "PAYMENT_CAPTURED",
                f"Genuine PayPal Sandbox Capture confirmed: {paypal_capture_id} (${amount:.2f} {currency}). Payment ID: {payment_id}. Net: ${calculated_net:.2f}.",
            )
            await office_service.send_speech_bubble(7, f"Verified payment captured! Ref: {payment_id}. Net ${calculated_net:.2f} credited.", "success", 4.0)

        if state.status == "AWAITING_PAYMENT":
            state.status = "RUNNING"
            state.current_step_index = 7
            state.current_step_name = SIMULATION_STEPS[7]
            return await self.execute_step(run_id)
        return state

    def sync_paypal_capture_sync(
        self,
        recovery_order_id: str,
        paypal_order_id: str,
        paypal_capture_id: str,
        amount: float,
        currency: str = "USD",
        fee_amount: float = 0.0,
        net_amount: Optional[float] = None,
        payment_id: Optional[str] = None,
        payer_id: Optional[str] = None,
        payer_email: Optional[str] = None,
        payer_name: Optional[str] = None,
    ) -> None:
        """Synchronously updates active simulation state with verified PayPal Sandbox payment capture."""
        target_state = None
        for s in self._active_simulations.values():
            if (s.offer_creation and s.offer_creation.get("order_id") == recovery_order_id) or (
                s.scenario_id == "SCENARIO_D" and s.status in ("AWAITING_PAYMENT", "RUNNING")
            ):
                target_state = s
                break
        if not target_state and self._default_sim_id in self._active_simulations:
            target_state = self._active_simulations[self._default_sim_id]

        if target_state:
            pid = payment_id or (
                target_state.paypal_checkout.get("payment_id") if target_state.paypal_checkout else f"PAY-SIM-{uuid.uuid4().hex[:8].upper()}"
            )
            calc_net = net_amount if net_amount is not None else round(amount - fee_amount, 2)
            buyer_details = {
                "payer_id": payer_id,
                "payer_email": payer_email,
                "payer_name": payer_name,
            }
            target_state.paypal_checkout = {
                "status": "CAPTURED",
                "payment_id": pid,
                "paypal_order_id": paypal_order_id,
                "paypal_capture_id": paypal_capture_id,
                "capture_id": paypal_capture_id,
                "recovery_order_id": recovery_order_id,
                "amount": amount,
                "currency": currency,
                "fee_amount": fee_amount,
                "net_amount": calc_net,
                "payer_id": payer_id,
                "payer_email": payer_email,
                "payer_name": payer_name,
                "buyer_details": buyer_details,
                "captured_at": datetime.utcnow().isoformat(),
                "is_live_sandbox": True,
                "capture_status": "COMPLETED",
                "payment_status": "CAPTURED",
                "reconciliation_status": "PENDING",
            }
            self._record_event(
                target_state,
                "Linda Zhang (Finance)",
                "PAYMENT_CAPTURED",
                f"Genuine PayPal Sandbox Capture confirmed: {paypal_capture_id} (${amount:.2f} {currency}). Payment ID: {pid}. Net: ${calc_net:.2f}.",
            )


# Global Singleton Orchestrator instance
simulation_orchestrator = SimulationOrchestrator()
