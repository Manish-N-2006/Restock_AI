import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..database import SessionLocal
from ..models.inventory import Inventory
from ..models.commerce import RecoveryOrder, RecoveryOrderStatus, RecoveryFulfillmentStatus
from ..payments.models import PaymentTransaction, PaymentStatus
from ..services.risk_engine import calculate_inventory_risk
from ..services.demand_engine import find_destination_candidates
from ..services.decision_engine import evaluate_decision
from ..services.logistics_engine import get_integrated_recommendation
from ..services.transfer_engine import get_transfer
from ..services.outcome_engine import get_outcome
from ..authorization.engine import authorize
from ..authorization.entities import build_user_entity, build_transfer_entity
from ..authorization.actions import Action
from ..office.service import office_service
from .llm import get_llm_model

logger = logging.getLogger(__name__)

# --- Structured Specialist Output Models ---

class InventoryAgentResult(BaseModel):
    agent_id: int = 2
    sku_id: str
    store_id: str
    product_name: str
    quantity: int
    days_to_expiry: int
    at_risk_quantity: int
    at_risk_value: float
    risk_level: str
    risk_score: float
    recommendation_summary: str


class RecoveryStrategyResult(BaseModel):
    agent_id: int = 3
    sku_id: str
    source_store_id: str
    selected_action: str
    recommended_quantity: int
    expected_net_recovery: float
    target_destination_store_id: Optional[str] = None
    candidate_destinations_count: int
    decision_reason: str


class LogisticsAgentResult(BaseModel):
    agent_id: int = 4
    sku_id: str
    source_store_id: str
    destination_store_id: str
    transfer_quantity: int
    selected_partner: str
    distance_km: float
    estimated_delivery_cost: float
    estimated_eta_minutes: int
    cold_chain_compliant: bool
    logistics_adjusted_net_recovery: float
    transfer_viable: bool
    reason: str


class CommerceAgentResult(BaseModel):
    agent_id: int = 5
    sku_id: str
    store_id: str
    action_type: str
    order_id: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    markdown_percentage: Optional[float] = None
    supplier_return_value: Optional[float] = None
    expected_net_recovery: float
    payment_status: Optional[str] = None
    reason: str


class FulfillmentAgentResult(BaseModel):
    agent_id: int = 6
    transfer_id: str
    status: str
    source_store_id: str
    destination_store_id: str
    quantity: int
    details: str


class FinanceAgentResult(BaseModel):
    agent_id: int = 7
    transfer_id: Optional[str] = None
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    captured_amount: Optional[float] = None
    fee_deducted: Optional[float] = None
    predicted_net_recovery: float
    actual_net_recovery: Optional[float] = None
    recovery_variance: Optional[float] = None
    reconciliation_status: str = "PENDING"
    audit_notes: str


class CEOOpsReport(BaseModel):
    scenario_id: str
    sku_id: str
    source_store_id: str
    product_name: str
    overall_status: str  # "COMPLETED" | "PENDING_APPROVAL" | "NO_ACTION_REQUIRED" | "FAILED"
    inventory_findings: Optional[InventoryAgentResult] = None
    strategy_recommendation: Optional[RecoveryStrategyResult] = None
    logistics_plan: Optional[LogisticsAgentResult] = None
    commerce_plan: Optional[CommerceAgentResult] = None
    fulfillment_summary: Optional[FulfillmentAgentResult] = None
    financial_audit: Optional[FinanceAgentResult] = None
    requires_human_approval: bool = False
    approval_id: Optional[str] = None
    approval_details: Optional[Dict[str, Any]] = None
    executive_summary: str
    timeline: List[Dict[str, Any]] = Field(default_factory=list)


# --- Global Pending Approvals Registry ---
pending_approvals: Dict[str, Dict[str, Any]] = {}


# --- Specialist Engine Execution Wrappers with Office Events ---

async def execute_inventory_agent(sku_id: str, store_id: str) -> InventoryAgentResult:
    """Executes the Inventory Agent (Agent 2) to audit stock and risk metrics."""
    agent_id = 2
    tool_id = f"inv-{int(time.time() * 1000)}"
    
    # 1. Visual Office Event: Agent receives task & activates
    await office_service.set_agent_active(agent_id, is_active=True)
    await office_service.start_tool(
        agent_id=agent_id,
        tool_id=tool_id,
        status=f"Auditing stock risk for {sku_id}",
        tool_name="CalculateRisk",
    )
    
    try:
        with SessionLocal() as db:
            inv = db.query(Inventory).filter(
                Inventory.sku_id == sku_id,
                Inventory.store_id == store_id
            ).first()
            if not inv:
                raise ValueError(f"No inventory record found for SKU {sku_id} at {store_id}")
            
            # Deterministic calculation via real risk_engine
            risk = calculate_inventory_risk(inv)
            
            result = InventoryAgentResult(
                agent_id=agent_id,
                sku_id=sku_id,
                store_id=store_id,
                product_name=inv.product_name,
                quantity=inv.quantity,
                days_to_expiry=risk.days_to_expiry,
                at_risk_quantity=risk.at_risk_quantity,
                at_risk_value=risk.at_risk_value,
                risk_level=risk.risk_level,
                risk_score=risk.risk_score,
                recommendation_summary=(
                    f"{inv.product_name}: {risk.at_risk_quantity}/{inv.quantity} units "
                    f"at {risk.risk_level} risk (days to expiry: {risk.days_to_expiry})."
                ),
            )
        
        # 2. Visual Office Event: Tool done & clear
        await office_service.done_tool(agent_id, tool_id)
        await office_service.clear_tools(agent_id)
        await office_service.set_agent_active(agent_id, is_active=False)
        return result
        
    except Exception as e:
        logger.error(f"Inventory Agent failed: {e}")
        await office_service.done_tool(agent_id, tool_id)
        await office_service.clear_tools(agent_id)
        await office_service.set_agent_active(agent_id, is_active=False)
        raise e


async def execute_recovery_strategy_agent(sku_id: str, source_store_id: str) -> RecoveryStrategyResult:
    """Executes Recovery Strategy Agent (Agent 3) using demand_engine and decision_engine."""
    agent_id = 3
    tool_id = f"rec-{int(time.time() * 1000)}"
    
    await office_service.set_agent_active(agent_id, is_active=True)
    await office_service.start_tool(
        agent_id=agent_id,
        tool_id=tool_id,
        status=f"Evaluating recovery decision for {sku_id}",
        tool_name="EvaluateDecision",
    )
    
    try:
        with SessionLocal() as db:
            destinations = find_destination_candidates(db, sku_id, source_store_id)
            decision = evaluate_decision(db, sku_id, source_store_id)
            
            candidate_count = len(destinations.candidates) if destinations and destinations.candidates else 0
            
            result = RecoveryStrategyResult(
                agent_id=agent_id,
                sku_id=sku_id,
                source_store_id=source_store_id,
                selected_action=decision.selected_action.value if hasattr(decision.selected_action, "value") else str(decision.selected_action),
                recommended_quantity=decision.recommended_quantity,
                expected_net_recovery=decision.expected_net_recovery,
                target_destination_store_id=decision.selected_destination_store_id,
                candidate_destinations_count=candidate_count,
                decision_reason=decision.decision_reason or "Automated recovery action selection.",
            )
            
        await office_service.done_tool(agent_id, tool_id)
        await office_service.clear_tools(agent_id)
        await office_service.set_agent_active(agent_id, is_active=False)
        return result
        
    except Exception as e:
        logger.error(f"Recovery Strategy Agent failed: {e}")
        await office_service.done_tool(agent_id, tool_id)
        await office_service.clear_tools(agent_id)
        await office_service.set_agent_active(agent_id, is_active=False)
        raise e


async def execute_logistics_agent(sku_id: str, source_store_id: str) -> LogisticsAgentResult:
    """Executes Logistics Agent (Agent 4) using logistics_engine."""
    agent_id = 4
    tool_id = f"log-{int(time.time() * 1000)}"
    
    await office_service.set_agent_active(agent_id, is_active=True)
    await office_service.start_tool(
        agent_id=agent_id,
        tool_id=tool_id,
        status=f"Optimizing transfer route for {sku_id}",
        tool_name="OptimizeLogistics",
    )
    
    try:
        with SessionLocal() as db:
            rec = get_integrated_recommendation(db, sku_id, source_store_id)
            
            if not rec.logistics or not rec.logistics.selected_partner:
                result = LogisticsAgentResult(
                    agent_id=agent_id,
                    sku_id=sku_id,
                    source_store_id=source_store_id,
                    destination_store_id=rec.decision.selected_destination_store_id or "",
                    transfer_quantity=rec.decision.recommended_quantity,
                    selected_partner="None",
                    distance_km=0.0,
                    estimated_delivery_cost=0.0,
                    estimated_eta_minutes=0,
                    cold_chain_compliant=False,
                    logistics_adjusted_net_recovery=rec.logistics_adjusted_net_recovery,
                    transfer_viable=False,
                    reason=rec.reason or "No compliant logistics partner found.",
                )
            else:
                partner = rec.logistics.selected_partner
                result = LogisticsAgentResult(
                    agent_id=agent_id,
                    sku_id=sku_id,
                    source_store_id=source_store_id,
                    destination_store_id=rec.decision.selected_destination_store_id or "",
                    transfer_quantity=rec.decision.recommended_quantity,
                    selected_partner=partner.partner_name,
                    distance_km=partner.distance_km,
                    estimated_delivery_cost=rec.logistics.delivery_cost,
                    estimated_eta_minutes=rec.logistics.eta_minutes,
                    cold_chain_compliant=partner.supports_cold_chain,
                    logistics_adjusted_net_recovery=rec.logistics_adjusted_net_recovery,
                    transfer_viable=rec.transfer_still_viable,
                    reason=rec.reason or "Logistics route verified.",
                )
                
        await office_service.done_tool(agent_id, tool_id)
        await office_service.clear_tools(agent_id)
        await office_service.set_agent_active(agent_id, is_active=False)
        return result
        
    except Exception as e:
        logger.error(f"Logistics Agent failed: {e}")
        await office_service.done_tool(agent_id, tool_id)
        await office_service.clear_tools(agent_id)
        await office_service.set_agent_active(agent_id, is_active=False)
        raise e


async def execute_commerce_agent(
    sku_id: str,
    source_store_id: str,
    quantity: int,
    unit_price: float,
    action_type: str = "DISCOUNT",
    channel: str = "DISCOUNT_MARKETPLACE",
) -> CommerceAgentResult:
    """
    Executes the Commerce Agent (Agent 5).
    Prepares an eligible commercial RecoveryOrder for secondary markets / discount clearance.
    Emits office events and leaves order in PENDING_PAYMENT awaiting buyer PayPal approval.
    """
    agent_id = 5
    tool_id = f"com-{int(time.time() * 1000)}"

    await office_service.set_agent_active(agent_id, is_active=True)
    await office_service.start_tool(
        agent_id=agent_id,
        tool_id=tool_id,
        status=f"Structuring recovery order for {sku_id}",
        tool_name="PrepareRecoveryOrder",
    )

    try:
        order_id = f"REC-ORD-{uuid.uuid4().hex[:8].upper()}"
        total_amount = round(quantity * unit_price, 2)
        
        with SessionLocal() as db:
            inv = db.query(Inventory).filter(
                Inventory.sku_id == sku_id,
                Inventory.store_id == source_store_id
            ).first()
            prod_name = inv.product_name if inv else sku_id

            order = RecoveryOrder(
                order_id=order_id,
                sku_id=sku_id,
                product_name=prod_name,
                source_store_id=source_store_id,
                channel=channel,
                quantity=quantity,
                unit_price=unit_price,
                total_amount=total_amount,
                currency="USD",
                status=RecoveryOrderStatus.PENDING_PAYMENT.value,
                fulfillment_status=RecoveryFulfillmentStatus.UNFULFILLED.value,
            )
            db.add(order)
            db.commit()

        result = CommerceAgentResult(
            agent_id=agent_id,
            sku_id=sku_id,
            store_id=source_store_id,
            action_type=action_type,
            order_id=order_id,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            expected_net_recovery=total_amount,
            payment_status=RecoveryOrderStatus.PENDING_PAYMENT.value,
            reason=f"Prepared commercial recovery order {order_id} ({quantity} units @ ${unit_price:.2f} = ${total_amount:.2f}). Awaiting PayPal payment.",
        )

        await office_service.done_tool(agent_id, tool_id)
        await office_service.clear_tools(agent_id)
        await office_service.set_agent_active(agent_id, is_active=False)
        return result

    except Exception as e:
        logger.error(f"Commerce Agent failed: {e}")
        await office_service.done_tool(agent_id, tool_id)
        await office_service.clear_tools(agent_id)
        await office_service.set_agent_active(agent_id, is_active=False)
        raise e


async def execute_finance_agent(
    payment_id: Optional[str] = None,
    recovery_order_id: Optional[str] = None,
    transfer_id: Optional[str] = None,
    predicted_net_recovery: float = 0.0,
) -> FinanceAgentResult:
    """
    Executes the Finance Agent (Agent 7).
    Audits financial projections, verifies captured PayPal transactions,
    and reconciles fees against expected margins.
    """
    agent_id = 7
    tool_id = f"fin-{int(time.time() * 1000)}"

    await office_service.set_agent_active(agent_id, is_active=True)
    await office_service.start_tool(
        agent_id=agent_id,
        tool_id=tool_id,
        status="Auditing financial ledger & reconciling payments",
        tool_name="ReconcilePayPalPayment",
    )

    try:
        captured_amount = None
        fee_deducted = None
        actual_net = None
        variance = None
        reconciliation_status = "PENDING_VERIFICATION"
        audit_notes = "Pre-settlement financial projection verified."

        with SessionLocal() as db:
            if payment_id or recovery_order_id:
                query = db.query(PaymentTransaction)
                if payment_id:
                    query = query.filter(PaymentTransaction.payment_id == payment_id)
                elif recovery_order_id:
                    query = query.filter(PaymentTransaction.recovery_order_id == recovery_order_id)
                
                txn = query.order_by(PaymentTransaction.created_at.desc()).first()
                if txn:
                    if txn.status == PaymentStatus.CAPTURED.value:
                        captured_amount = txn.amount
                        fee_deducted = txn.fee_amount
                        actual_net = txn.net_amount
                        variance = round(actual_net - predicted_net_recovery, 2)
                        reconciliation_status = "RECONCILED"
                        audit_notes = (
                            f"Verified PayPal Capture {txn.paypal_capture_id}: Gross ${captured_amount:.2f}, "
                            f"PayPal Fee: ${fee_deducted:.2f}, Net: ${actual_net:.2f}. "
                            f"Variance vs predicted: ${variance:+.2f}."
                        )
                    else:
                        audit_notes = f"Payment record {txn.payment_id} status is {txn.status}. Awaiting buyer PayPal authorization."
                else:
                    audit_notes = f"Commercial order {recovery_order_id} awaiting buyer payment authorization."

        result = FinanceAgentResult(
            agent_id=agent_id,
            transfer_id=transfer_id,
            payment_id=payment_id,
            order_id=recovery_order_id,
            captured_amount=captured_amount,
            fee_deducted=fee_deducted,
            predicted_net_recovery=predicted_net_recovery,
            actual_net_recovery=actual_net,
            recovery_variance=variance,
            reconciliation_status=reconciliation_status,
            audit_notes=audit_notes,
        )

        await office_service.done_tool(agent_id, tool_id)
        await office_service.clear_tools(agent_id)
        await office_service.set_agent_active(agent_id, is_active=False)
        return result

    except Exception as e:
        logger.error(f"Finance Agent failed: {e}")
        await office_service.done_tool(agent_id, tool_id)
        await office_service.clear_tools(agent_id)
        await office_service.set_agent_active(agent_id, is_active=False)
        raise e


async def execute_fulfillment_agent(
    transfer_id: Optional[str] = None,
    order_id: Optional[str] = None,
    source_store_id: str = "STORE_A",
    destination_store_id: str = "STORE_B",
    quantity: int = 0,
) -> FulfillmentAgentResult:
    """Executes Fulfillment Agent (Agent 6) for warehouse dispatch and staging."""
    agent_id = 6
    tool_id = f"ful-{int(time.time() * 1000)}"

    await office_service.set_agent_active(agent_id, is_active=True)
    await office_service.start_tool(
        agent_id=agent_id,
        tool_id=tool_id,
        status="Executing warehouse fulfillment & carrier handoff",
        tool_name="DispatchFulfillment",
    )
    try:
        details = (
            f"Transfer manifest {transfer_id} staged for carrier pickup."
            if transfer_id
            else f"Commercial order {order_id} inventory reserved and staged at Dock Bay 2."
        )
        result = FulfillmentAgentResult(
            agent_id=agent_id,
            transfer_id=transfer_id or (order_id or "N/A"),
            status="STAGED",
            source_store_id=source_store_id,
            destination_store_id=destination_store_id,
            quantity=quantity,
            details=details,
        )
        await office_service.done_tool(agent_id, tool_id)
        await office_service.clear_tools(agent_id)
        await office_service.set_agent_active(agent_id, is_active=False)
        return result
    except Exception as e:
        logger.error(f"Fulfillment Agent failed: {e}")
        await office_service.done_tool(agent_id, tool_id)
        await office_service.clear_tools(agent_id)
        await office_service.set_agent_active(agent_id, is_active=False)
        raise e


# --- CEO Supervisor Multi-Agent Orchestration ---

async def run_workforce_recovery_orchestration(
    sku_id: str,
    source_store_id: str,
    principal: Optional[Dict[str, Any]] = None,
    auto_approve: bool = False,
) -> CEOOpsReport:
    """
    CEO / Operations Agent multi-agent orchestration workflow.
    Delegates tasks to specialist agents:
      CEO (1) -> Inventory Agent (2) -> Recovery Strategy Agent (3) -> Logistics Agent (4)
    Collects structured outputs, evaluates Cedar authorization, and produces CEOOpsReport.
    """
    scenario_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
    timeline: List[Dict[str, Any]] = []

    def record_step(agent_name: str, action: str, details: str):
        timeline.append({
            "timestamp": time.strftime("%H:%M:%S"),
            "agent": agent_name,
            "action": action,
            "details": details,
        })

    # Default principal for manager role if not provided
    if principal is None:
        principal = build_user_entity(user_id="manager-agent", role="MANAGER", store_scope="*")

    logger.info(f"Starting workforce orchestration for {sku_id} at {source_store_id}")
    record_step("CEO Agent", "TASK_STARTED", f"Initiated inventory recovery analysis for {sku_id} at {source_store_id}")

    # Step 1: CEO activates at workstation
    await office_service.set_agent_active(1, is_active=True)
    await office_service.start_tool(1, f"ceo-{int(time.time()*1000)}", "Orchestrating Workforce", "SuperviseRecovery")

    inv_result: Optional[InventoryAgentResult] = None
    rec_result: Optional[RecoveryStrategyResult] = None
    log_result: Optional[LogisticsAgentResult] = None
    com_result: Optional[CommerceAgentResult] = None
    fin_result: Optional[FinanceAgentResult] = None

    try:
        # Step 2: Delegate to Inventory Agent (2)
        record_step("CEO Agent", "TASK_ASSIGNED", "Assigned risk audit to Inventory Agent (Agent 2)")
        inv_result = await execute_inventory_agent(sku_id, source_store_id)
        record_step("Inventory Agent", "TASK_COMPLETED", inv_result.recommendation_summary)

        # Step 3: If item has at-risk quantity, delegate to Recovery Strategy Agent (3)
        if inv_result.at_risk_quantity > 0:
            record_step("CEO Agent", "TASK_ASSIGNED", "Assigned candidate evaluation to Recovery Strategy Agent (Agent 3)")
            rec_result = await execute_recovery_strategy_agent(sku_id, source_store_id)
            record_step(
                "Recovery Strategy Agent",
                "TASK_COMPLETED",
                f"Action selected: {rec_result.selected_action} (expected net: ${rec_result.expected_net_recovery})"
            )

            # Step 4: If action is TRANSFER, delegate to Logistics Agent (4)
            if rec_result.selected_action == "TRANSFER":
                record_step("CEO Agent", "TASK_ASSIGNED", "Assigned route optimization to Logistics Agent (Agent 4)")
                log_result = await execute_logistics_agent(sku_id, source_store_id)
                record_step(
                    "Logistics Agent",
                    "TASK_COMPLETED",
                    f"Selected partner: {log_result.selected_partner}, viable={log_result.transfer_viable}"
                )

        # Step 5: Check Cedar Authorization for Transfer Actions (STEP 7)
        requires_approval = False
        approval_id = None
        approval_details = None
        overall_status = "COMPLETED"

        if rec_result and rec_result.selected_action == "TRANSFER" and log_result and log_result.transfer_viable:
            # Check Cedar authorization policy
            transfer_res_entity = build_transfer_entity(
                transfer_id=f"TR-PLANNED-{scenario_id}",
                source_store_id=source_store_id,
                status="CREATED"
            )
            authz_check = authorize(
                principal_entity=principal,
                action=Action.APPROVE_TRANSFER.value,
                resource_entity=transfer_res_entity
            )

            # In operational workflows, transfers above risk threshold or policy limits require human sign-off
            if not auto_approve:
                requires_approval = True
                approval_id = f"APP-{uuid.uuid4().hex[:6].upper()}"
                approval_details = {
                    "approval_id": approval_id,
                    "scenario_id": scenario_id,
                    "sku_id": sku_id,
                    "source_store_id": source_store_id,
                    "destination_store_id": rec_result.target_destination_store_id,
                    "quantity": rec_result.recommended_quantity,
                    "selected_partner": log_result.selected_partner,
                    "net_recovery": log_result.logistics_adjusted_net_recovery,
                    "cedar_allowed": authz_check.allowed,
                    "status": "PENDING",
                    "created_at": time.time(),
                }
                pending_approvals[approval_id] = approval_details
                overall_status = "PENDING_APPROVAL"

                # Visual office event: move agent to approval waiting area
                record_step("Logistics Agent", "APPROVAL_REQUIRED", f"Transfer requires human authorization. Approval ID: {approval_id}")
                await office_service.move_agent_to(4, "approval")
                await office_service.set_permission(4, required=True)
            else:
                record_step("CEO Agent", "MANAGER_APPROVED", "Automatic approval policy applied.")

            # Step 5a: Finance Agent audits logistics & projected transfer margins
            record_step("CEO Agent", "TASK_ASSIGNED", "Assigned ledger audit to Finance Agent (Agent 7)")
            fin_result = await execute_finance_agent(
                transfer_id=f"TR-PLANNED-{scenario_id}",
                predicted_net_recovery=log_result.logistics_adjusted_net_recovery,
            )
            record_step("Finance Agent", "TASK_COMPLETED", fin_result.audit_notes)

        elif rec_result and rec_result.selected_action in ("DISCOUNT", "BUNDLE", "RETURN", "LIQUIDATION"):
            # Step 5b: Commerce Agent structures commercial recovery order
            record_step("CEO Agent", "TASK_ASSIGNED", "Assigned commercial recovery order creation to Commerce Agent (Agent 5)")
            unit_price = round(inv_result.at_risk_value / max(1, inv_result.at_risk_quantity) * 0.7, 2)
            com_result = await execute_commerce_agent(
                sku_id=sku_id,
                source_store_id=source_store_id,
                quantity=rec_result.recommended_quantity,
                unit_price=unit_price,
                action_type=rec_result.selected_action,
                channel="DISCOUNT_MARKETPLACE" if rec_result.selected_action == "DISCOUNT" else "LIQUIDATION",
            )
            record_step(
                "Commerce Agent",
                "TASK_COMPLETED",
                f"Generated order {com_result.order_id} ({com_result.quantity} units, total ${com_result.total_amount:.2f}). Awaiting PayPal payment.",
            )

            # Step 5c: Finance Agent audits pre-settlement commercial ledger
            record_step("CEO Agent", "TASK_ASSIGNED", "Assigned payment reconciliation tracking to Finance Agent (Agent 7)")
            fin_result = await execute_finance_agent(
                recovery_order_id=com_result.order_id,
                predicted_net_recovery=com_result.expected_net_recovery,
            )
            record_step("Finance Agent", "TASK_COMPLETED", fin_result.audit_notes)

        elif inv_result and inv_result.at_risk_quantity == 0:
            overall_status = "NO_ACTION_REQUIRED"

        # Step 6: Produce Final Executive Summary
        exec_summary = (
            f"Workforce Audit Summary for {inv_result.product_name} ({sku_id}): "
            f"Risk Level: {inv_result.risk_level}. "
        )
        if rec_result:
            exec_summary += f"Optimal Strategy: {rec_result.selected_action}. "
        if log_result and log_result.transfer_viable:
            exec_summary += (
                f"Logistics verified via {log_result.selected_partner} to {log_result.destination_store_id} "
                f"({log_result.distance_km} km, ${log_result.estimated_delivery_cost} cost). "
                f"Logistics Adjusted Net Recovery: ${log_result.logistics_adjusted_net_recovery}."
            )
        if com_result:
            exec_summary += (
                f" Commercial Order Prepared: {com_result.order_id} (${com_result.total_amount:.2f} USD). "
                f"Status: {com_result.payment_status}."
            )
        if fin_result:
            exec_summary += f" Financial Audit: {fin_result.audit_notes}"
        if requires_approval:
            exec_summary += f" [Status: Awaiting Human Approval ({approval_id})]"

        report = CEOOpsReport(
            scenario_id=scenario_id,
            sku_id=sku_id,
            source_store_id=source_store_id,
            product_name=inv_result.product_name if inv_result else sku_id,
            overall_status=overall_status,
            inventory_findings=inv_result,
            strategy_recommendation=rec_result,
            logistics_plan=log_result,
            commerce_plan=com_result,
            financial_audit=fin_result,
            requires_human_approval=requires_approval,
            approval_id=approval_id,
            approval_details=approval_details,
            executive_summary=exec_summary,
            timeline=timeline,
        )

        record_step("CEO Agent", "TASK_COMPLETED", "Produced CEO Operational Report")
        return report

    finally:
        # Reset CEO state
        await office_service.clear_tools(1)
        await office_service.set_agent_active(1, is_active=False)
