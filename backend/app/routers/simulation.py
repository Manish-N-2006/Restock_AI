"""
Simulation 2.0 API Router
Exposes control endpoints for the unified autonomous simulation center.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services.simulation_orchestrator import (
    simulation_orchestrator,
    SimulationState,
)
from ..services.buyer_matching import match_buyers, BuyerMatchResult

router = APIRouter(prefix="/api/simulation", tags=["Simulation 2.0"])

class ResetSimulationRequest(BaseModel):
    scenario_type: str = "SCENARIO_A"  # "SCENARIO_A" | "SCENARIO_B" | "SCENARIO_C" | "SCENARIO_D"

class ApprovalDecisionRequest(BaseModel):
    run_id: Optional[str] = None
    decision: str = "APPROVED"  # "APPROVED" | "REJECTED"

class PayPalConfirmRequest(BaseModel):
    run_id: Optional[str] = None
    payment_id: Optional[str] = None
    paypal_order_id: str
    paypal_capture_id: str
    amount: float
    currency: str = "USD"
    fee_amount: Optional[float] = 0.0
    net_amount: Optional[float] = None
    payer_id: Optional[str] = None
    payer_email: Optional[str] = None
    payer_name: Optional[str] = None

class SpeedRequest(BaseModel):
    run_id: Optional[str] = None
    speed: float = 1.0  # 1.0, 2.0, 5.0

@router.get("/state", response_model=SimulationState)
async def get_simulation_state(run_id: Optional[str] = Query(None)):
    """Returns the current isolated simulation state."""
    return simulation_orchestrator.get_current_simulation(run_id)

@router.post("/step", response_model=SimulationState)
async def step_simulation(run_id: Optional[str] = Query(None)):
    """Executes the next step in the 9-stage simulation pipeline."""
    return await simulation_orchestrator.execute_step(run_id)

@router.post("/reset", response_model=SimulationState)
async def reset_simulation(req: ResetSimulationRequest):
    """Resets the simulation runtime with a designated scenario."""
    return await simulation_orchestrator.reset_simulation(req.scenario_type)

@router.post("/run", response_model=SimulationState)
async def run_simulation(run_id: Optional[str] = Query(None)):
    """Runs simulation steps until completion or approval pause."""
    state = simulation_orchestrator.get_current_simulation(run_id)
    state.status = "RUNNING"
    while state.status == "RUNNING" and state.current_step_index < 9:
        prev_idx = state.current_step_index
        state = await simulation_orchestrator.execute_step(run_id)
        if state.status in ("AWAITING_APPROVAL", "AWAITING_PAYMENT", "COMPLETED", "REJECTED"):
            break
        if state.current_step_index == prev_idx:
            break
    return state

@router.post("/pause", response_model=SimulationState)
async def pause_simulation(run_id: Optional[str] = Query(None)):
    """Pauses the simulation."""
    state = simulation_orchestrator.get_current_simulation(run_id)
    if state.status == "RUNNING":
        state.status = "PAUSED"
    return state

@router.post("/resume", response_model=SimulationState)
async def resume_simulation(run_id: Optional[str] = Query(None)):
    """Resumes the simulation."""
    state = simulation_orchestrator.get_current_simulation(run_id)
    if state.status == "PAUSED":
        state.status = "RUNNING"
        return await run_simulation(run_id)
    return state

@router.post("/approve", response_model=SimulationState)
async def approve_simulation_decision(req: ApprovalDecisionRequest):
    """Submits manager approval or rejection for the pending Cedar policy check."""
    return await simulation_orchestrator.approve_pending_decision(req.run_id, req.decision)

@router.post("/paypal/confirm", response_model=SimulationState)
async def confirm_simulation_paypal(req: PayPalConfirmRequest):
    """Confirms live PayPal Sandbox payment capture for simulation order."""
    return await simulation_orchestrator.confirm_paypal_capture(
        run_id=req.run_id,
        payment_id=req.payment_id,
        paypal_order_id=req.paypal_order_id,
        paypal_capture_id=req.paypal_capture_id,
        amount=req.amount,
        currency=req.currency,
        fee_amount=req.fee_amount or 0.0,
        net_amount=req.net_amount,
        payer_id=req.payer_id,
        payer_email=req.payer_email,
        payer_name=req.payer_name,
    )

@router.get("/buyers/candidates", response_model=List[BuyerMatchResult])
async def get_buyer_candidates(
    sku_id: str = "YOG-001",
    product_name: str = "Greek Yogurt 500g",
    quantity: int = 120,
    unit_price: float = 1.50,
):
    """Queries deterministic buyer candidates using the Buyer Matching Engine."""
    return match_buyers(
        sku_id=sku_id,
        product_name=product_name,
        quantity=quantity,
        unit_price=unit_price,
    )
