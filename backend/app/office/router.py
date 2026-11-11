import asyncio
import logging
import os
import time
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel

from .service import office_service
from ..auth.service import validate_websocket_origin, verify_websocket_session
from ..agent.workforce import (
    run_workforce_recovery_orchestration,
    pending_approvals,
    CEOOpsReport,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/office", tags=["Virtual Office"])


def verify_dev_environment():
    """Ensures test and simulation endpoints are strictly disabled outside development/test environments."""
    env = os.getenv("RESTOCKAI_ENV", "development").lower()
    if env not in ("development", "dev", "test"):
        raise HTTPException(
            status_code=403,
            detail="Office test endpoints are disabled outside development environments.",
        )


class AgentStatusRequest(BaseModel):
    agent_id: int
    is_active: bool
    awaiting_input: bool = False


class ToolStartRequest(BaseModel):
    agent_id: int
    tool_id: str
    status: str
    tool_name: Optional[str] = None
    permission_active: bool = False


class ToolDoneRequest(BaseModel):
    agent_id: int
    tool_id: str


class PermissionRequest(BaseModel):
    agent_id: int
    required: bool


class SimulateSequenceRequest(BaseModel):
    agent_id: int = 2
    task_name: str = "Auditing inventory risk for SKU-104"
    tool_name: str = "InspectStock"
    step_delay_sec: float = 2.0


class MoveAgentRequest(BaseModel):
    agent_id: int
    destination: str  # "workstation" | "conference" | "approval" | "breakroom"


class TriggerWorkflowRequest(BaseModel):
    sku_id: str = "YOG-001"
    source_store_id: str = "STORE_A"
    auto_approve: bool = False


class ApprovalDecisionRequest(BaseModel):
    approval_id: str
    decision: str  # "APPROVED" | "REJECTED"
    approver: str = "manager-1"
    notes: Optional[str] = None


# --- WebSocket Endpoint (/ws/office) ---

async def handle_office_websocket(websocket: WebSocket):
    if not validate_websocket_origin(websocket):
        await websocket.close(code=1008, reason="Untrusted WebSocket origin")
        return

    session = verify_websocket_session(websocket)
    if not session:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await office_service.connect(websocket, session_jti=session["jti"])
    try:
        while True:
            # Keep listening for client messages (heartbeats, webviewReady, seat saves, etc.)
            data = await websocket.receive_text()
            logger.debug(f"Received from office client: {data}")
            try:
                import json
                msg = json.loads(data)
                msg_type = msg.get("type")
                if msg_type == "webviewReady":
                    logger.info("Received webviewReady from office client; sending hydration.")
                    await office_service.send_hydration(websocket)
                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
                elif msg_type == "saveAgentSeats":
                    seats = msg.get("seats")
                    if isinstance(seats, dict):
                        office_service.update_seats(seats)
            except Exception as parse_err:
                logger.debug(f"Non-fatal error parsing client message: {parse_err}")
    except WebSocketDisconnect:
        await office_service.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection error: {e}")
        await office_service.disconnect(websocket)


# --- Core Operational & State Endpoints ---

@router.get("/state")
async def get_office_state():
    """Get the current live state of all office agents and active connections."""
    return {
        "active_clients": len(office_service.active_websockets),
        "agents": {
            a.id: {
                "name": a.name,
                "department": a.department,
                "palette": a.palette,
                "status": a.status,
                "awaiting_input": a.awaiting_input,
                "current_tool": a.current_tool,
                "permission_active": a.permission_active,
            }
            for a in office_service.agents.values()
        },
    }


@router.post("/agent/move")
async def move_agent_endpoint(req: MoveAgentRequest):
    """Dispatch an agent to a specific office room/area using A* pathfinding."""
    if req.agent_id not in office_service.agents:
        raise HTTPException(status_code=404, detail=f"Agent {req.agent_id} not found")
    valid_destinations = ["workstation", "conference", "approval", "breakroom"]
    if req.destination not in valid_destinations:
        raise HTTPException(status_code=400, detail=f"Invalid destination. Must be one of {valid_destinations}")
    await office_service.move_agent_to(req.agent_id, req.destination)
    return {
        "status": "ok",
        "agent_id": req.agent_id,
        "destination": req.destination,
        "message": f"Agent {req.agent_id} walking to {req.destination}",
    }


# --- Controlled Workflow Trigger (Phase 2 - Step 6) ---

@router.post("/workflow/trigger", response_model=CEOOpsReport)
async def trigger_workforce_workflow(req: TriggerWorkflowRequest):
    """
    Triggers an actual multi-agent inventory recovery analysis through CEO Agent.
    Executes: CEO -> Inventory Agent -> Recovery Strategy Agent -> Logistics Agent -> CEO report.
    """
    report = await run_workforce_recovery_orchestration(
        sku_id=req.sku_id,
        source_store_id=req.source_store_id,
        auto_approve=req.auto_approve,
    )
    return report


# --- Human Approval & Cedar Authorization Integration (Phase 2 - Step 7) ---

@router.get("/approval/pending")
async def list_pending_approvals():
    """List all workflows currently awaiting human approval."""
    pending = [a for a in pending_approvals.values() if a.get("status") == "PENDING"]
    return {
        "pending_count": len(pending),
        "approvals": pending,
    }


@router.post("/approval/decision")
async def submit_approval_decision(req: ApprovalDecisionRequest):
    """Submit a human manager approval or rejection for a pending agent transfer."""
    if req.approval_id not in pending_approvals:
        raise HTTPException(status_code=404, detail=f"Approval request {req.approval_id} not found")

    item = pending_approvals[req.approval_id]
    if item["status"] != "PENDING":
        raise HTTPException(status_code=400, detail=f"Approval request is already {item['status']}")

    decision_upper = req.decision.upper()
    if decision_upper not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=400, detail="Decision must be APPROVED or REJECTED")

    item["status"] = decision_upper
    item["decided_by"] = req.approver
    item["decision_timestamp"] = time.time()
    item["notes"] = req.notes

    # Clear permission badge and return Logistics Agent to workstation
    await office_service.set_permission(4, required=False)
    await office_service.move_agent_to(4, "workstation")

    return {
        "status": "ok",
        "approval_id": req.approval_id,
        "decision": decision_upper,
        "approver": req.approver,
        "message": f"Transfer workflow resumed with decision: {decision_upper}",
    }


# --- Development / Test-Only Endpoints (Protected by verify_dev_environment) ---

@router.post("/test/simulate-sequence", dependencies=[Depends(verify_dev_environment)])
async def simulate_sequence(req: SimulateSequenceRequest, background_tasks: BackgroundTasks):
    """Triggers the test integration sequence for development verification."""
    if req.agent_id not in office_service.agents:
        raise HTTPException(status_code=404, detail=f"Agent {req.agent_id} not found")

    async def _run_sequence():
        await office_service.set_agent_active(req.agent_id, is_active=True)
        if req.step_delay_sec > 0:
            await asyncio.sleep(req.step_delay_sec)

        tool_id = f"task-{int(time.time())}"
        await office_service.start_tool(
            agent_id=req.agent_id,
            tool_id=tool_id,
            status=req.task_name,
            tool_name=req.tool_name,
        )
        if req.step_delay_sec > 0:
            await asyncio.sleep(req.step_delay_sec * 2)

        await office_service.done_tool(agent_id=req.agent_id, tool_id=tool_id)
        await office_service.clear_tools(agent_id=req.agent_id)
        if req.step_delay_sec > 0:
            await asyncio.sleep(req.step_delay_sec)

        await office_service.set_agent_active(req.agent_id, is_active=False)

    asyncio.create_task(_run_sequence())
    return {
        "status": "started",
        "agent_id": req.agent_id,
        "task_name": req.task_name,
        "message": "Integration sequence running asynchronously",
    }


@router.post("/test/agent-status", dependencies=[Depends(verify_dev_environment)])
async def update_agent_status(req: AgentStatusRequest):
    """Update an agent's active status."""
    if req.agent_id not in office_service.agents:
        raise HTTPException(status_code=404, detail=f"Agent {req.agent_id} not found")
    await office_service.set_agent_active(req.agent_id, req.is_active, req.awaiting_input)
    return {"status": "ok", "agent_id": req.agent_id}


@router.post("/test/tool-start", dependencies=[Depends(verify_dev_environment)])
async def start_tool_endpoint(req: ToolStartRequest):
    """Trigger a tool start event on an agent."""
    if req.agent_id not in office_service.agents:
        raise HTTPException(status_code=404, detail=f"Agent {req.agent_id} not found")
    await office_service.start_tool(
        req.agent_id,
        req.tool_id,
        req.status,
        req.tool_name,
        req.permission_active,
    )
    return {"status": "ok", "agent_id": req.agent_id}


@router.post("/test/tool-done", dependencies=[Depends(verify_dev_environment)])
async def done_tool_endpoint(req: ToolDoneRequest):
    """Trigger a tool done event on an agent."""
    if req.agent_id not in office_service.agents:
        raise HTTPException(status_code=404, detail=f"Agent {req.agent_id} not found")
    await office_service.done_tool(req.agent_id, req.tool_id)
    return {"status": "ok", "agent_id": req.agent_id}


@router.post("/test/permission", dependencies=[Depends(verify_dev_environment)])
async def permission_endpoint(req: PermissionRequest):
    """Set or clear a permission prompt on an agent."""
    if req.agent_id not in office_service.agents:
        raise HTTPException(status_code=404, detail=f"Agent {req.agent_id} not found")
    await office_service.set_permission(req.agent_id, req.required)
    return {"status": "ok", "agent_id": req.agent_id, "permission_required": req.required}


@router.post("/test/reset", dependencies=[Depends(verify_dev_environment)])
async def reset_endpoint(agent_id: Optional[int] = None):
    """Reset one or all agents back to idle."""
    if agent_id:
        if agent_id not in office_service.agents:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        await office_service.reset_agent_idle(agent_id)
    else:
        await office_service.reset_all()
    return {"status": "ok", "reset_agent_id": agent_id}
