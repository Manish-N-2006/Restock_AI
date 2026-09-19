from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.inventory import Inventory
from ..schemas.decision import (
    RecoveryActionType,
    EvaluatedAction,
    DecisionResponse,
    DecisionSummaryResponse
)
from .risk_engine import calculate_inventory_risk
from .demand_engine import find_destination_candidates

# Configurable constants for deterministic assumptions
MINIMUM_NET_RECOVERY = 0.0

# TRANSFER
BASE_TRANSFER_COST = 20.0
COST_PER_KM = 2.5
TRANSFER_HANDLING_COST = 10.0

# DISCOUNT
DEFAULT_DISCOUNT_PERCENTAGE = 0.20
DEFAULT_DISCOUNT_SELL_THROUGH = 0.70

# BUNDLE
BUNDLE_PRICE_DISCOUNT = 0.15
BUNDLE_SELL_THROUGH = 0.60
BUNDLE_HANDLING_COST = 5.0

# PROMOTE
DEFAULT_PROMOTION_UPLIFT = 0.25
PROMOTION_HANDLING_COST = 15.0
PROMOTION_SELL_THROUGH = 0.80

# RETURN
RETURN_HANDLING_COST = 15.0
RETURN_LOGISTICS_COST = 30.0

# DISPOSE
DISPOSAL_COST_PER_UNIT = 5.0

def evaluate_transfer(db: Session, inv: Inventory, at_risk_quantity: int) -> EvaluatedAction:
    matches = find_destination_candidates(db, sku_id=inv.sku_id, source_store_id=inv.store_id)
    
    if not matches.candidates:
        return EvaluatedAction(
            action=RecoveryActionType.TRANSFER,
            available=False,
            quantity=0,
            expected_recovered_value=0.0,
            logistics_cost=0.0,
            handling_cost=0.0,
            risk_cost=0.0,
            expected_net_recovery=0.0,
            economically_viable=False,
            assumptions=["Requires an eligible destination store"],
            reason="No eligible destination store found within range."
        )
        
    best_match = matches.candidates[0]
    qty = best_match.recommended_transfer_quantity
    
    expected_recovered_value = qty * inv.selling_price
    logistics_cost = BASE_TRANSFER_COST + (best_match.distance_km * COST_PER_KM)
    handling_cost = qty * TRANSFER_HANDLING_COST
    expected_net_recovery = expected_recovered_value - logistics_cost - handling_cost
    
    viable = expected_net_recovery > MINIMUM_NET_RECOVERY
    
    return EvaluatedAction(
        action=RecoveryActionType.TRANSFER,
        available=True,
        quantity=qty,
        expected_recovered_value=round(expected_recovered_value, 2),
        logistics_cost=round(logistics_cost, 2),
        handling_cost=round(handling_cost, 2),
        risk_cost=0.0,
        expected_net_recovery=round(expected_net_recovery, 2),
        economically_viable=viable,
        assumptions=[f"Transfer to {best_match.destination_store_id}"],
        reason=f"Can transfer {qty} units to {best_match.destination_store_id} with positive expected net recovery." if viable else "Transfer logistics and handling costs exceed expected recovered value."
    )

def evaluate_discount(inv: Inventory, at_risk_quantity: int) -> EvaluatedAction:
    qty = int(at_risk_quantity * DEFAULT_DISCOUNT_SELL_THROUGH)
    if qty == 0:
        return EvaluatedAction(
            action=RecoveryActionType.DISCOUNT,
            available=False,
            quantity=0,
            expected_recovered_value=0.0,
            logistics_cost=0.0,
            handling_cost=0.0,
            risk_cost=0.0,
            expected_net_recovery=0.0,
            economically_viable=False,
            assumptions=["Sell-through must result in at least 1 unit"],
            reason="Discount assumption yields zero expected sales."
        )

    discounted_price = inv.selling_price * (1.0 - DEFAULT_DISCOUNT_PERCENTAGE)
    expected_recovered_value = qty * discounted_price
    # Discount doesn't move physical goods, just margin impact which is inherent in the reduced recovered value
    expected_net_recovery = expected_recovered_value
    viable = expected_net_recovery > MINIMUM_NET_RECOVERY

    return EvaluatedAction(
        action=RecoveryActionType.DISCOUNT,
        available=True,
        quantity=qty,
        expected_recovered_value=round(expected_recovered_value, 2),
        logistics_cost=0.0,
        handling_cost=0.0,
        risk_cost=0.0,
        expected_net_recovery=round(expected_net_recovery, 2),
        economically_viable=viable,
        assumptions=[
            f"{int(DEFAULT_DISCOUNT_PERCENTAGE*100)}% markdown assumption",
            f"{int(DEFAULT_DISCOUNT_SELL_THROUGH*100)}% expected sell-through assumption"
        ],
        reason=f"Discounting produces positive expected recovery of {round(expected_net_recovery, 2)}." if viable else "Discount yields negative or zero net recovery."
    )

def evaluate_bundle(inv: Inventory, at_risk_quantity: int) -> EvaluatedAction:
    qty = int(at_risk_quantity * BUNDLE_SELL_THROUGH)
    if qty == 0:
        return EvaluatedAction(
            action=RecoveryActionType.BUNDLE,
            available=False,
            quantity=0,
            expected_recovered_value=0.0,
            logistics_cost=0.0,
            handling_cost=0.0,
            risk_cost=0.0,
            expected_net_recovery=0.0,
            economically_viable=False,
            assumptions=["Requires bundle match logic"],
            reason="No viable bundle scenario exists."
        )
        
    bundled_price = inv.selling_price * (1.0 - BUNDLE_PRICE_DISCOUNT)
    expected_recovered_value = qty * bundled_price
    handling_cost = qty * BUNDLE_HANDLING_COST
    expected_net_recovery = expected_recovered_value - handling_cost
    viable = expected_net_recovery > MINIMUM_NET_RECOVERY
    
    return EvaluatedAction(
        action=RecoveryActionType.BUNDLE,
        available=True,
        quantity=qty,
        expected_recovered_value=round(expected_recovered_value, 2),
        logistics_cost=0.0,
        handling_cost=round(handling_cost, 2),
        risk_cost=0.0,
        expected_net_recovery=round(expected_net_recovery, 2),
        economically_viable=viable,
        assumptions=[
            f"{int(BUNDLE_PRICE_DISCOUNT*100)}% price adjustment for bundle",
            f"{int(BUNDLE_SELL_THROUGH*100)}% expected bundle sell-through assumption"
        ],
        reason="Bundling produces positive expected recovery." if viable else "Bundling costs exceed expected recovery."
    )

def evaluate_promote(inv: Inventory, at_risk_quantity: int) -> EvaluatedAction:
    # Promote increases baseline sales
    additional_expected = int(inv.daily_sales_7d * DEFAULT_PROMOTION_UPLIFT)
    qty = min(additional_expected, at_risk_quantity)
    
    if qty == 0:
        return EvaluatedAction(
            action=RecoveryActionType.PROMOTE,
            available=False,
            quantity=0,
            expected_recovered_value=0.0,
            logistics_cost=0.0,
            handling_cost=0.0,
            risk_cost=0.0,
            expected_net_recovery=0.0,
            economically_viable=False,
            assumptions=["Promotion uplift assumption"],
            reason="Expected promotion uplift does not translate to additional units sold."
        )
        
    expected_recovered_value = qty * inv.selling_price
    handling_cost = PROMOTION_HANDLING_COST
    expected_net_recovery = expected_recovered_value - handling_cost
    viable = expected_net_recovery > MINIMUM_NET_RECOVERY
    
    return EvaluatedAction(
        action=RecoveryActionType.PROMOTE,
        available=True,
        quantity=qty,
        expected_recovered_value=round(expected_recovered_value, 2),
        logistics_cost=0.0,
        handling_cost=round(handling_cost, 2),
        risk_cost=0.0,
        expected_net_recovery=round(expected_net_recovery, 2),
        economically_viable=viable,
        assumptions=[f"{int(DEFAULT_PROMOTION_UPLIFT*100)}% demand uplift assumption"],
        reason="Promotion generates positive net recovery." if viable else "Promotion cost exceeds uplift value."
    )

def evaluate_return(inv: Inventory, at_risk_quantity: int) -> EvaluatedAction:
    if not inv.return_allowed or inv.supplier_return_value is None:
        return EvaluatedAction(
            action=RecoveryActionType.RETURN,
            available=False,
            quantity=0,
            expected_recovered_value=0.0,
            logistics_cost=0.0,
            handling_cost=0.0,
            risk_cost=0.0,
            expected_net_recovery=0.0,
            economically_viable=False,
            assumptions=["Requires return agreement"],
            reason="Return to supplier is not allowed for this product."
        )
        
    expected_recovered_value = at_risk_quantity * inv.supplier_return_value
    expected_net_recovery = expected_recovered_value - RETURN_LOGISTICS_COST - RETURN_HANDLING_COST
    viable = expected_net_recovery > MINIMUM_NET_RECOVERY
    
    return EvaluatedAction(
        action=RecoveryActionType.RETURN,
        available=True,
        quantity=at_risk_quantity,
        expected_recovered_value=round(expected_recovered_value, 2),
        logistics_cost=RETURN_LOGISTICS_COST,
        handling_cost=RETURN_HANDLING_COST,
        risk_cost=0.0,
        expected_net_recovery=round(expected_net_recovery, 2),
        economically_viable=viable,
        assumptions=["Supplier honors predefined return value per unit"],
        reason="Return produces positive net recovery." if viable else "Return costs exceed supplier refund."
    )

def evaluate_dispose(inv: Inventory, at_risk_quantity: int) -> EvaluatedAction:
    handling_cost = at_risk_quantity * DISPOSAL_COST_PER_UNIT
    expected_net_recovery = -handling_cost
    
    return EvaluatedAction(
        action=RecoveryActionType.DISPOSE,
        available=True,
        quantity=at_risk_quantity,
        expected_recovered_value=0.0,
        logistics_cost=0.0,
        handling_cost=round(handling_cost, 2),
        risk_cost=0.0,
        expected_net_recovery=round(expected_net_recovery, 2),
        economically_viable=False, # Always false because net recovery <= 0
        assumptions=[f"Cost of {DISPOSAL_COST_PER_UNIT} per unit to dispose"],
        reason="Disposal is a net-negative fallback action."
    )

def evaluate_no_action(inv: Inventory, reason: str = "No action necessary or economically viable") -> EvaluatedAction:
    return EvaluatedAction(
        action=RecoveryActionType.NO_ACTION,
        available=True,
        quantity=0,
        expected_recovered_value=0.0,
        logistics_cost=0.0,
        handling_cost=0.0,
        risk_cost=0.0,
        expected_net_recovery=0.0,
        economically_viable=True, # Valid fallback
        assumptions=[],
        reason=reason
    )

def evaluate_decision(db: Session, sku_id: str, store_id: str, min_risk: str = "HIGH") -> DecisionResponse:
    inv = db.query(Inventory).filter(Inventory.sku_id == sku_id, Inventory.store_id == store_id).first()
    if not inv:
        return DecisionResponse(
            sku_id=sku_id,
            store_id=store_id,
            risk=None,
            actions=[evaluate_no_action(inv, "SKU not found.")],
            selected_action=RecoveryActionType.NO_ACTION,
            recommended_quantity=0,
            expected_net_recovery=0.0,
            decision_reason="Item not found."
        )

    risk = calculate_inventory_risk(inv)
    risk_hierarchy = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    
    if risk_hierarchy.get(risk.risk_level, 0) < risk_hierarchy.get(min_risk, 3) or risk.at_risk_quantity <= 0:
        no_action = evaluate_no_action(inv, f"Risk level is {risk.risk_level}, which is below actionable threshold.")
        return DecisionResponse(
            sku_id=sku_id,
            store_id=store_id,
            risk=risk,
            actions=[no_action],
            selected_action=RecoveryActionType.NO_ACTION,
            recommended_quantity=0,
            expected_net_recovery=0.0,
            decision_reason="No recovery action is economically viable under the current assumptions (risk too low)."
        )

    actions = [
        evaluate_transfer(db, inv, risk.at_risk_quantity),
        evaluate_discount(inv, risk.at_risk_quantity),
        evaluate_bundle(inv, risk.at_risk_quantity),
        evaluate_promote(inv, risk.at_risk_quantity),
        evaluate_return(inv, risk.at_risk_quantity),
        evaluate_dispose(inv, risk.at_risk_quantity)
    ]
    
    # Filter viable positive actions
    viable_actions = [a for a in actions if a.available and a.economically_viable and a.expected_net_recovery > 0]
    
    if not viable_actions:
        no_act = evaluate_no_action(inv, "No recovery action is economically viable under the current assumptions.")
        actions.append(no_act)
        return DecisionResponse(
            sku_id=sku_id,
            store_id=store_id,
            risk=risk,
            actions=actions,
            selected_action=RecoveryActionType.NO_ACTION,
            recommended_quantity=0,
            expected_net_recovery=0.0,
            decision_reason="No recovery action is economically viable under the current assumptions."
        )
        
    # Tie-breaking logic:
    # 1. Higher expected net recovery
    # 2. Higher recovered value (gross)
    # 3. Lower complexity (mapped via action type roughly: DISCOUNT/PROMOTE > BUNDLE > RETURN > TRANSFER)
    complexity_map = {
        RecoveryActionType.DISCOUNT: 1,
        RecoveryActionType.PROMOTE: 2,
        RecoveryActionType.BUNDLE: 3,
        RecoveryActionType.RETURN: 4,
        RecoveryActionType.TRANSFER: 5
    }
    
    viable_actions.sort(key=lambda a: (
        a.expected_net_recovery,
        a.expected_recovered_value,
        -complexity_map.get(a.action, 99)
    ), reverse=True)
    
    best = viable_actions[0]
    
    dest_store = None
    if best.action == RecoveryActionType.TRANSFER:
        dest_store = best.assumptions[0].replace("Transfer to ", "")
        
    # Create final response
    reason_str = ""
    if best.action == RecoveryActionType.TRANSFER:
        reason_str = f"Transfer to {dest_store} is recommended because it produces the highest positive expected net recovery of {best.expected_net_recovery}."
    elif best.action == RecoveryActionType.DISCOUNT:
        reason_str = f"Discount is recommended because there is no better viable destination store and local markdown produces positive expected recovery of {best.expected_net_recovery}."
    else:
        reason_str = f"{best.action.value.capitalize()} produces the highest positive expected net recovery of {best.expected_net_recovery}."

    return DecisionResponse(
        sku_id=sku_id,
        store_id=store_id,
        risk=risk,
        actions=actions + [evaluate_no_action(inv, "Omitted in favor of better action")],
        selected_action=best.action,
        selected_destination_store_id=dest_store,
        recommended_quantity=best.quantity,
        expected_net_recovery=best.expected_net_recovery,
        decision_reason=reason_str
    )

def get_decision_summary(db: Session) -> DecisionSummaryResponse:
    all_inv = db.query(Inventory).all()
    
    summary = DecisionSummaryResponse(
        total_at_risk_items=0,
        items_with_viable_recovery=0,
        recommended_transfers=0,
        recommended_discounts=0,
        recommended_bundles=0,
        recommended_promotions=0,
        recommended_returns=0,
        recommended_disposals=0,
        no_action_items=0,
        total_expected_net_recovery=0.0
    )
    
    for inv in all_inv:
        risk = calculate_inventory_risk(inv)
        if risk.risk_level in ["HIGH", "CRITICAL"] and risk.at_risk_quantity > 0:
            summary.total_at_risk_items += 1
            decision = evaluate_decision(db, inv.sku_id, inv.store_id)
            
            if decision.selected_action != RecoveryActionType.NO_ACTION:
                summary.items_with_viable_recovery += 1
                summary.total_expected_net_recovery += decision.expected_net_recovery
                
            if decision.selected_action == RecoveryActionType.TRANSFER:
                summary.recommended_transfers += 1
            elif decision.selected_action == RecoveryActionType.DISCOUNT:
                summary.recommended_discounts += 1
            elif decision.selected_action == RecoveryActionType.BUNDLE:
                summary.recommended_bundles += 1
            elif decision.selected_action == RecoveryActionType.PROMOTE:
                summary.recommended_promotions += 1
            elif decision.selected_action == RecoveryActionType.RETURN:
                summary.recommended_returns += 1
            elif decision.selected_action == RecoveryActionType.DISPOSE:
                summary.recommended_disposals += 1
            elif decision.selected_action == RecoveryActionType.NO_ACTION:
                summary.no_action_items += 1
                
    return summary

def get_all_decisions(db: Session) -> List[DecisionResponse]:
    all_inv = db.query(Inventory).all()
    decisions = []
    
    for inv in all_inv:
        risk = calculate_inventory_risk(inv)
        if risk.risk_level in ["HIGH", "CRITICAL"] and risk.at_risk_quantity > 0:
            decision = evaluate_decision(db, inv.sku_id, inv.store_id)
            decisions.append(decision)
            
    return decisions
