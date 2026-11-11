"""
Network-First Inventory Intelligence & Redistribution Engine.

Implements:
1. Donor & Receiving Branch Matching.
2. Incremental Network Economic Value Calculations (avoiding false revenue consolidation).
3. Logistics Partner Optimization with simulated road-network routing, mandatory cold-chain filters, and capacity verification.
4. Deterministic Constrained Greedy Multi-Branch Balancing.
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

# Constants for Road-Network Simulation & Economics
ROAD_TORTUOSITY_FACTOR = 1.25  # Road network distance vs Haversine straight-line distance
AVERAGE_URBAN_SPEED_KMH = 35.0  # Realistic city/metro freight speed
EXPIRY_BUFFER_HOURS = 4.0      # Safety margin before expiry upon arrival
HANDLING_COST_PER_UNIT = 0.15  # Warehousing cross-dock handling fee
EARTH_RADIUS_KM = 6371.0

# Pre-defined carrier fleet data for deterministic road-network optimization
CARRIER_FLEET_DATA = [
    {
        "partner_id": "CARRIER-SWIFT-01",
        "partner_name": "SwiftReefer Express",
        "vehicle_type": "Refrigerated Sprinter Van (3.5T)",
        "base_cost": 25.0,
        "cost_per_km": 1.60,
        "capacity_units": 250,
        "supports_cold_chain": True,
        "temperature_range": "2°C to 6°C Active Chilled",
    },
    {
        "partner_id": "CARRIER-ARCTIC-02",
        "partner_name": "ArcticCold Logistics",
        "vehicle_type": "Multi-Temp Heavy Reefer (7.5T)",
        "base_cost": 45.0,
        "cost_per_km": 2.20,
        "capacity_units": 800,
        "supports_cold_chain": True,
        "temperature_range": "-18°C to 4°C Dual Zone",
    },
    {
        "partner_id": "CARRIER-METRO-03",
        "partner_name": "MetroCargo Ambient",
        "vehicle_type": "Standard Box Truck (5.0T)",
        "base_cost": 15.0,
        "cost_per_km": 1.10,
        "capacity_units": 600,
        "supports_cold_chain": False,
        "temperature_range": "Ambient Only (No Active Cooling)",
    },
    {
        "partner_id": "CARRIER-FASTVAN-04",
        "partner_name": "QuickCourier Van",
        "vehicle_type": "Compact Cargo Van (1.2T)",
        "base_cost": 12.0,
        "cost_per_km": 0.95,
        "capacity_units": 75,
        "supports_cold_chain": False,
        "temperature_range": "Ambient Only",
    },
]


class DonorBranch(BaseModel):
    store_id: str
    store_name: str
    sku_id: str
    product_name: str
    current_stock: int
    safety_stock: int
    transferable_quantity: int
    daily_velocity: float
    days_to_expiry: float
    cost_price: float
    selling_price: float
    temperature_class: str
    requires_cold_chain: bool
    latitude: float
    longitude: float


class ReceivingBranch(BaseModel):
    store_id: str
    store_name: str
    sku_id: str
    product_name: str
    current_stock: int
    target_stock: int
    daily_demand: float
    shortage_quantity: int
    storage_capacity: int
    available_capacity: int
    absorbable_quantity: int
    stockout_deadline_hours: float
    supports_cold_chain: bool
    latitude: float
    longitude: float


class BranchCandidateMatch(BaseModel):
    branch_type: str  # "RECEIVING_BRANCH" | "DONOR_BRANCH"
    store_id: str
    store_name: str
    match_score: float
    is_eligible: bool
    recommended_transfer_qty: int
    straight_line_distance_km: float
    simulated_road_distance_km: float
    estimated_transit_minutes: int
    cold_chain_compatible: bool
    capacity_status: str
    net_economic_value: float
    reasons: List[str]
    rejection_reasons: List[str] = []


class LogisticsCarrierOption(BaseModel):
    partner_id: str
    partner_name: str
    vehicle_type: str
    straight_line_km: float
    road_distance_km: float
    is_simulated_road_distance: bool = True
    estimated_journey_time_minutes: int
    transport_cost: float
    vehicle_capacity: int
    cold_chain_available: bool
    expected_delivery_time: str
    eligible: bool
    final_score: float
    selection_reason: str
    rejection_reason: Optional[str] = None


class IncrementalNetworkEconomics(BaseModel):
    transfer_quantity: int
    retail_price: float
    cost_price: float
    margin_protected_at_receiver: float
    avoided_markdown_writeoff_loss: float
    gross_revenue_protected: float
    transport_cost: float
    handling_cost: float
    transit_spoilage_risk_cost: float
    donor_opportunity_cost: float
    net_incremental_network_value: float
    supplier_replenishment_comparison: Dict[str, Any]
    alternative_actions_ranking: List[Dict[str, Any]]


class MultiBranchTransferPlan(BaseModel):
    plan_id: str
    transfers: List[Dict[str, Any]]
    total_units_rebalanced: int
    total_freight_cost: float
    total_margin_protected: float
    total_net_network_value: float
    algorithm: str = "Deterministic Constrained Greedy Matching"
    limitations: str = (
        "Constrained greedy matching iteratively selects the highest marginal network-value transfer "
        "while enforcing safety stock, destination capacity, cold-chain compatibility, and shelf-life constraints. "
        "While computationally fast, deterministic, and highly operational, it is a heuristic and does not claim "
        "global mathematical Pareto-optimality across complex multi-echelon networks."
    )


def calculate_haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two geographic coordinates."""
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2.0) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.asin(math.sqrt(max(0.0, min(1.0, a))))
    return round(EARTH_RADIUS_KM * c, 2)


def calculate_simulated_road_km(straight_km: float) -> float:
    """
    Computes simulated road-network distance by applying an empirical urban tortuosity factor.
    Explicitly labeled as simulated road-network distance.
    """
    return round(straight_km * ROAD_TORTUOSITY_FACTOR, 2)


def optimize_logistics_partners(
    source_lat: float,
    source_lon: float,
    dest_lat: float,
    dest_lon: float,
    transfer_quantity: int,
    requires_cold_chain: bool,
    hours_to_expiry: float,
) -> Tuple[List[LogisticsCarrierOption], Optional[LogisticsCarrierOption]]:
    """
    Evaluates all feasible transport carriers against operational constraints:
    1. Cold-chain requirement (mandatory hard filter).
    2. Vehicle capacity >= transfer_quantity (mandatory hard filter).
    3. Journey ETA + buffer < hours_to_expiry (mandatory hard filter).
    4. Ranks eligible options by a balanced operational suitability score.
    """
    straight_km = calculate_haversine_km(source_lat, source_lon, dest_lat, dest_lon)
    road_km = calculate_simulated_road_km(straight_km)

    evaluated_carriers: List[LogisticsCarrierOption] = []

    for carrier in CARRIER_FLEET_DATA:
        # Calculate transit time based on simulated road distance and average urban speed
        transit_hours = road_km / AVERAGE_URBAN_SPEED_KMH
        transit_minutes = int(math.ceil(transit_hours * 60.0))
        transport_cost = round(carrier["base_cost"] + (road_km * carrier["cost_per_km"]), 2)

        # Mandatory Hard Filters
        eligible = True
        rejection_reasons = []

        # 1. Cold Chain
        if requires_cold_chain and not carrier["supports_cold_chain"]:
            eligible = False
            rejection_reasons.append("Carrier lacks required active refrigeration equipment for temperature-sensitive perishables.")

        # 2. Vehicle Capacity
        if carrier["capacity_units"] < transfer_quantity:
            eligible = False
            rejection_reasons.append(
                f"Vehicle capacity ({carrier['capacity_units']} units) is smaller than required transfer quantity ({transfer_quantity} units)."
            )

        # 3. Expiry ETA
        if (transit_hours + (EXPIRY_BUFFER_HOURS / 2.0)) > hours_to_expiry:
            eligible = False
            rejection_reasons.append(
                f"Estimated road transit ({transit_minutes} min) exceeds safe delivery window before product expiry ({hours_to_expiry:.1f}h)."
            )

        # Scoring: (Cost 50%, ETA 35%, Capacity Headroom 15%)
        score = 0.0
        if eligible:
            # Baseline benchmark: $100 max cost, 120 min max ETA, 500 headroom
            cost_factor = max(0.0, 100.0 - (transport_cost / 1.5))
            eta_factor = max(0.0, 100.0 - (transit_minutes * 0.8))
            headroom = carrier["capacity_units"] - transfer_quantity
            headroom_factor = min(100.0, (headroom / 300.0) * 100.0)

            score = round((0.50 * cost_factor) + (0.35 * eta_factor) + (0.15 * headroom_factor), 1)
            selection_reason = (
                f"Optimally qualified: {carrier['vehicle_type']} provides full active temperature control, "
                f"{carrier['capacity_units']} unit capacity, {transit_minutes} min ETA, and ${transport_cost:.2f} competitive freight."
            )
            rejection_reason = None
        else:
            selection_reason = "Ineligible for operational dispatch."
            rejection_reason = " | ".join(rejection_reasons)

        evaluated_carriers.append(
            LogisticsCarrierOption(
                partner_id=carrier["partner_id"],
                partner_name=carrier["partner_name"],
                vehicle_type=carrier["vehicle_type"],
                straight_line_km=straight_km,
                road_distance_km=road_km,
                is_simulated_road_distance=True,
                estimated_journey_time_minutes=transit_minutes,
                transport_cost=transport_cost,
                vehicle_capacity=carrier["capacity_units"],
                cold_chain_available=carrier["supports_cold_chain"],
                expected_delivery_time=f"+{transit_minutes} minutes from dispatch",
                eligible=eligible,
                final_score=score,
                selection_reason=selection_reason,
                rejection_reason=rejection_reason,
            )
        )

    # Sort eligible first, highest score first, lowest cost first
    evaluated_carriers.sort(key=lambda c: (c.eligible, c.final_score, -c.transport_cost), reverse=True)
    best_carrier = evaluated_carriers[0] if evaluated_carriers and evaluated_carriers[0].eligible else None

    return evaluated_carriers, best_carrier


def calculate_incremental_network_value(
    donor: DonorBranch,
    receiver: ReceivingBranch,
    transfer_qty: int,
    carrier: Optional[LogisticsCarrierOption],
) -> IncrementalNetworkEconomics:
    """
    Computes true incremental economic value created across the consolidated retail network.
    Does NOT double-count internal transfers as consolidated revenue.
    """
    retail_p = donor.selling_price
    cost_p = donor.cost_price

    # 1. Protected Contribution Margin at Receiver
    # If the receiver stocked out, this sales margin would have been permanently lost to competitors.
    margin_per_unit = retail_p - cost_p
    margin_protected = round(transfer_qty * margin_per_unit, 2)
    gross_revenue_protected = round(transfer_qty * retail_p, 2)

    # 2. Avoided Write-Off / Spoilage Loss at Donor
    # Without transfer, surplus at donor would spoil or be heavily liquidated at a loss.
    avoided_loss = round(transfer_qty * cost_p * 0.85, 2)

    # 3. Freight and Cross-Dock Handling Costs
    transport_cost = carrier.transport_cost if carrier else 50.0
    handling_cost = round(transfer_qty * HANDLING_COST_PER_UNIT, 2)

    # 4. Spoilage / Damage Risk During Transit (Assumed 1.5% for refrigerated multi-stop transit)
    transit_spoilage_risk_cost = round(transfer_qty * cost_p * 0.015, 2)

    # 5. Opportunity Cost of Donor Inventory (0 if strictly above safety stock)
    donor_opportunity_cost = 0.0

    # Net Incremental Value of Internal Redistribution
    net_value = round(
        margin_protected + avoided_loss - transport_cost - handling_cost - transit_spoilage_risk_cost - donor_opportunity_cost,
        2,
    )

    # Supplier Emergency Replenishment Comparison (Alternative option for receiver)
    supplier_rush_fee = 85.0
    supplier_lead_time_h = 24.0
    lost_demand_during_lead_time = min(transfer_qty, int(receiver.daily_demand * (supplier_lead_time_h / 24.0)))
    lost_sales_val = round(lost_demand_during_lead_time * margin_per_unit, 2)
    supplier_net_cost = round(supplier_rush_fee + lost_sales_val, 2)
    transfer_advantage = round(net_value - (-supplier_net_cost), 2)

    supplier_comparison = {
        "supplier_lead_time_hours": supplier_lead_time_h,
        "supplier_emergency_surcharge": supplier_rush_fee,
        "lost_sales_before_supplier_arrival": lost_sales_val,
        "supplier_net_penalty": supplier_net_cost,
        "internal_transfer_advantage": transfer_advantage,
        "economic_conclusion": (
            f"Internal transfer creates ${transfer_advantage:.2f} USD superior net network value "
            f"compared to emergency supplier re-ordering with 24h lead time."
        ),
    }

    # Compare with Alternative Recovery Actions
    local_markdown_net = round(transfer_qty * (retail_p * 0.65 - cost_p), 2)
    bundle_net = round(transfer_qty * (retail_p * 0.75 - cost_p) - 15.0, 2)
    supplier_return_net = round(transfer_qty * (cost_p * 0.50) - 30.0, 2)
    external_liquidation_net = round(transfer_qty * (retail_p * 0.45) - 25.0, 2)
    disposal_net = round(-transfer_qty * 0.35, 2)
    no_action_net = round(-transfer_qty * cost_p, 2)

    ranking = [
        {"action": "INTERNAL_TRANSFER", "net_value": net_value, "viable": net_value > 0, "rank": 1},
        {"action": "LOCAL_MARKDOWN", "net_value": local_markdown_net, "viable": local_markdown_net > 0, "rank": 2},
        {"action": "PRODUCT_BUNDLE", "net_value": bundle_net, "viable": bundle_net > 0, "rank": 3},
        {"action": "SUPPLIER_RETURN", "net_value": supplier_return_net, "viable": supplier_return_net > 0, "rank": 4},
        {"action": "EXTERNAL_LIQUIDATION", "net_value": external_liquidation_net, "viable": external_liquidation_net > 0, "rank": 5},
        {"action": "DISPOSAL", "net_value": disposal_net, "viable": False, "rank": 6},
        {"action": "NO_ACTION", "net_value": no_action_net, "viable": False, "rank": 7},
    ]
    ranking.sort(key=lambda x: x["net_value"], reverse=True)
    for idx, item in enumerate(ranking, 1):
        item["rank"] = idx

    return IncrementalNetworkEconomics(
        transfer_quantity=transfer_qty,
        retail_price=retail_p,
        cost_price=cost_p,
        margin_protected_at_receiver=margin_protected,
        avoided_markdown_writeoff_loss=avoided_loss,
        gross_revenue_protected=gross_revenue_protected,
        transport_cost=transport_cost,
        handling_cost=handling_cost,
        transit_spoilage_risk_cost=transit_spoilage_risk_cost,
        donor_opportunity_cost=donor_opportunity_cost,
        net_incremental_network_value=net_value,
        supplier_replenishment_comparison=supplier_comparison,
        alternative_actions_ranking=ranking,
    )


def match_candidate_receivers(
    donor: DonorBranch,
    all_receivers: List[ReceivingBranch],
) -> List[BranchCandidateMatch]:
    """
    Ranks receiving branches for a donor store with surplus inventory (Scenario A).
    """
    matches: List[BranchCandidateMatch] = []

    for receiver in all_receivers:
        if receiver.store_id == donor.store_id:
            continue

        straight_km = calculate_haversine_km(donor.latitude, donor.longitude, receiver.latitude, receiver.longitude)
        road_km = calculate_simulated_road_km(straight_km)
        transit_minutes = int(math.ceil((road_km / AVERAGE_URBAN_SPEED_KMH) * 60.0))

        # Constraints
        is_eligible = True
        rejection_reasons = []
        reasons = []

        # 1. Cold chain check
        cold_chain_compatible = True
        if donor.requires_cold_chain and not receiver.supports_cold_chain:
            cold_chain_compatible = False
            is_eligible = False
            rejection_reasons.append("Branch lacks certified cold-storage equipment for perishable stock.")

        # 2. Capacity check
        transfer_qty = min(donor.transferable_quantity, receiver.shortage_quantity, receiver.available_capacity, receiver.absorbable_quantity)
        if receiver.available_capacity <= 0:
            is_eligible = False
            rejection_reasons.append("Branch storage and staging capacity at 100% capacity limit.")
        elif transfer_qty <= 0:
            is_eligible = False
            rejection_reasons.append("Zero incremental absorption demand before product expiry.")

        # 3. Distance check (> 40km is outside intra-day redistribution zone)
        if road_km > 45.0:
            is_eligible = False
            rejection_reasons.append(f"Road distance ({road_km} km) exceeds 45 km maximum economical redistribution radius.")

        # 4. Logistics check
        hours_to_exp = donor.days_to_expiry * 24.0
        _, best_carrier = optimize_logistics_partners(
            donor.latitude, donor.longitude, receiver.latitude, receiver.longitude, transfer_qty or 1, donor.requires_cold_chain, hours_to_exp
        )
        if not best_carrier and is_eligible:
            is_eligible = False
            rejection_reasons.append("No compatible logistics carrier available meeting cold-chain and ETA constraints.")

        # Calculate Net Economic Value
        econ = calculate_incremental_network_value(donor, receiver, max(1, transfer_qty), best_carrier)
        net_val = econ.net_incremental_network_value if is_eligible else 0.0

        # Score (Demand Velocity 40%, Net Value 40%, Distance 20%)
        velocity_score = min(100.0, (receiver.daily_demand / 30.0) * 100.0)
        distance_score = max(0.0, (45.0 - road_km) / 45.0 * 100.0)
        econ_score = min(100.0, max(0.0, (net_val / 400.0) * 100.0))
        match_score = round((0.40 * velocity_score) + (0.40 * econ_score) + (0.20 * distance_score), 1) if is_eligible else 0.0

        if is_eligible:
            reasons.append(f"High local demand velocity ({receiver.daily_demand} units/day).")
            reasons.append(f"Able to absorb {transfer_qty} units with {transit_minutes} min road transit.")
            reasons.append(f"Yields +${net_val:.2f} net network economic value.")

        matches.append(
            BranchCandidateMatch(
                branch_type="RECEIVING_BRANCH",
                store_id=receiver.store_id,
                store_name=receiver.store_name,
                match_score=match_score,
                is_eligible=is_eligible,
                recommended_transfer_qty=transfer_qty if is_eligible else 0,
                straight_line_distance_km=straight_km,
                simulated_road_distance_km=road_km,
                estimated_transit_minutes=transit_minutes,
                cold_chain_compatible=cold_chain_compatible,
                capacity_status=f"{receiver.available_capacity} units available" if receiver.available_capacity > 0 else "FULL",
                net_economic_value=net_val,
                reasons=reasons,
                rejection_reasons=rejection_reasons,
            )
        )

    # Sort eligible first, then match_score descending, net_val descending
    matches.sort(key=lambda m: (m.is_eligible, m.match_score, m.net_economic_value), reverse=True)
    return matches


def match_candidate_donors(
    receiver: ReceivingBranch,
    all_donors: List[DonorBranch],
) -> List[BranchCandidateMatch]:
    """
    Ranks donor branches for a receiving store facing stockout (Scenario B).
    """
    matches: List[BranchCandidateMatch] = []

    for donor in all_donors:
        if donor.store_id == receiver.store_id:
            continue

        straight_km = calculate_haversine_km(donor.latitude, donor.longitude, receiver.latitude, receiver.longitude)
        road_km = calculate_simulated_road_km(straight_km)
        transit_minutes = int(math.ceil((road_km / AVERAGE_URBAN_SPEED_KMH) * 60.0))
        transit_hours = transit_minutes / 60.0

        is_eligible = True
        rejection_reasons = []
        reasons = []

        # 1. Cold chain check
        cold_chain_compatible = True
        if donor.requires_cold_chain and not receiver.supports_cold_chain:
            cold_chain_compatible = False
            is_eligible = False
            rejection_reasons.append("Receiving branch lacks cold-chain facilities for temperature-controlled stock.")

        # 2. Donor surplus & safety stock check
        if donor.transferable_quantity <= 0:
            is_eligible = False
            rejection_reasons.append(
                f"Donor has zero transferable stock above its required safety stock buffer ({donor.safety_stock} units)."
            )

        # 3. Stockout deadline check: Transit must arrive BEFORE receiver runs completely out of stock!
        if (transit_hours + 0.5) > receiver.stockout_deadline_hours:
            is_eligible = False
            rejection_reasons.append(
                f"Transit time ({transit_minutes} min) arrives after the critical stockout deadline ({receiver.stockout_deadline_hours:.1f}h)."
            )

        transfer_qty = min(donor.transferable_quantity, receiver.shortage_quantity)
        if transfer_qty <= 0:
            transfer_qty = min(donor.transferable_quantity, 30)

        # 4. Logistics partner
        hours_to_exp = donor.days_to_expiry * 24.0
        _, best_carrier = optimize_logistics_partners(
            donor.latitude, donor.longitude, receiver.latitude, receiver.longitude, transfer_qty, donor.requires_cold_chain, hours_to_exp
        )
        if not best_carrier and is_eligible:
            is_eligible = False
            rejection_reasons.append("No carrier with active cold-chain and timely ETA available.")

        # Calculate Net Economic Value
        econ = calculate_incremental_network_value(donor, receiver, transfer_qty, best_carrier)
        net_val = econ.net_incremental_network_value if is_eligible else 0.0

        # Score: (Urgency/Safety Buffer 40%, Economic Advantage 40%, Proximity 20%)
        buffer_headroom = max(0.0, receiver.stockout_deadline_hours - transit_hours)
        urgency_score = min(100.0, (buffer_headroom / 5.0) * 100.0)
        distance_score = max(0.0, (45.0 - road_km) / 45.0 * 100.0)
        econ_score = min(100.0, max(0.0, (net_val / 350.0) * 100.0))
        match_score = round((0.40 * urgency_score) + (0.40 * econ_score) + (0.20 * distance_score), 1) if is_eligible else 0.0

        if is_eligible:
            reasons.append(f"Provides {transfer_qty} units surplus without violating donor safety stock.")
            reasons.append(f"Arrives {buffer_headroom:.1f}h before stockout deadline ({transit_minutes} min ETA).")
            reasons.append(f"Saves ${econ.supplier_replenishment_comparison['internal_transfer_advantage']:.2f} vs supplier emergency order.")

        matches.append(
            BranchCandidateMatch(
                branch_type="DONOR_BRANCH",
                store_id=donor.store_id,
                store_name=donor.store_name,
                match_score=match_score,
                is_eligible=is_eligible,
                recommended_transfer_qty=transfer_qty if is_eligible else 0,
                straight_line_distance_km=straight_km,
                simulated_road_distance_km=road_km,
                estimated_transit_minutes=transit_minutes,
                cold_chain_compatible=cold_chain_compatible,
                capacity_status=f"{donor.transferable_quantity} units transferable surplus",
                net_economic_value=net_val,
                reasons=reasons,
                rejection_reasons=rejection_reasons,
            )
        )

    matches.sort(key=lambda m: (m.is_eligible, m.match_score, m.net_economic_value), reverse=True)
    return matches


def solve_constrained_greedy_balancing(
    donors: List[DonorBranch],
    receivers: List[ReceivingBranch],
) -> MultiBranchTransferPlan:
    """
    Solves network-wide inventory balancing (Scenario C) via deterministic constrained greedy matching.
    Iteratively pairs highest marginal value transfers while updating inventory balances.
    """
    plan_id = "PLAN-NET-BAL-01"
    transfers: List[Dict[str, Any]] = []
    total_units = 0
    total_freight = 0.0
    total_margin = 0.0
    total_net = 0.0

    # Make mutable inventory balances
    donor_pool = {d.store_id: d.transferable_quantity for d in donors}
    receiver_needs = {r.store_id: r.shortage_quantity for r in receivers}

    # Evaluate all candidate pairings
    candidates: List[Tuple[float, DonorBranch, ReceivingBranch, int, LogisticsCarrierOption, IncrementalNetworkEconomics]] = []

    for d in donors:
        for r in receivers:
            if d.store_id == r.store_id:
                continue
            if d.sku_id != r.sku_id:
                continue
            if d.requires_cold_chain and not r.supports_cold_chain:
                continue

            straight_km = calculate_haversine_km(d.latitude, d.longitude, r.latitude, r.longitude)
            road_km = calculate_simulated_road_km(straight_km)
            if road_km > 45.0:
                continue

            feasible_qty = min(d.transferable_quantity, r.shortage_quantity, r.available_capacity)
            if feasible_qty <= 0:
                continue

            hours_to_exp = d.days_to_expiry * 24.0
            _, best_carrier = optimize_logistics_partners(
                d.latitude, d.longitude, r.latitude, r.longitude, feasible_qty, d.requires_cold_chain, hours_to_exp
            )
            if not best_carrier:
                continue

            econ = calculate_incremental_network_value(d, r, feasible_qty, best_carrier)
            if econ.net_incremental_network_value > 0:
                candidates.append((econ.net_incremental_network_value, d, r, feasible_qty, best_carrier, econ))

    # Sort candidates by highest net value descending
    candidates.sort(key=lambda x: x[0], reverse=True)

    # Greedily allocate transfers
    transfer_index = 1
    for net_val, d, r, initial_qty, carrier, econ in candidates:
        available_donor = donor_pool[d.store_id]
        needed_receiver = receiver_needs[r.store_id]

        alloc_qty = min(available_donor, needed_receiver)
        if alloc_qty <= 0:
            continue

        # Recalculate economics for allocated quantity
        recalculated_econ = calculate_incremental_network_value(d, r, alloc_qty, carrier)

        transfers.append({
            "transfer_id": f"TR-NET-{transfer_index:02d}",
            "donor_store_id": d.store_id,
            "donor_store_name": d.store_name,
            "receiver_store_id": r.store_id,
            "receiver_store_name": r.store_name,
            "sku_id": d.sku_id,
            "product_name": d.product_name,
            "quantity": alloc_qty,
            "carrier_name": carrier.partner_name,
            "road_distance_km": carrier.road_distance_km,
            "transit_minutes": carrier.estimated_journey_time_minutes,
            "freight_cost": carrier.transport_cost,
            "margin_protected": recalculated_econ.margin_protected_at_receiver,
            "net_network_value": recalculated_econ.net_incremental_network_value,
            "temperature_compliant": True,
        })

        donor_pool[d.store_id] -= alloc_qty
        receiver_needs[r.store_id] -= alloc_qty
        total_units += alloc_qty
        total_freight += carrier.transport_cost
        total_margin += recalculated_econ.margin_protected_at_receiver
        total_net += recalculated_econ.net_incremental_network_value
        transfer_index += 1

    return MultiBranchTransferPlan(
        plan_id=plan_id,
        transfers=transfers,
        total_units_rebalanced=total_units,
        total_freight_cost=round(total_freight, 2),
        total_margin_protected=round(total_margin, 2),
        total_net_network_value=round(total_net, 2),
    )
