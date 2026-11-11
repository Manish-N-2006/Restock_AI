import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.service import reset_auth_runtime_state
from app.office.events import (
    ExistingAgents,
    AgentSeatMeta,
    AgentStatus,
    AgentToolStart,
    AgentToolDone,
    AgentToolsClear,
    AgentToolPermission,
    AgentToolPermissionClear,
    AgentTeamInfo,
    LayoutLoaded,
)
from app.office.service import office_service


def test_office_event_serialization():
    """Verify typed event models serialize to exact Pixel Agents JSON protocol."""
    # 1. ExistingAgents
    existing = ExistingAgents(
        agents=[1, 2],
        agentMeta={"1": AgentSeatMeta(palette=0, seatId="seat-1"), "2": AgentSeatMeta(palette=1)},
        directoryNames={"1": "Operations", "2": "Inventory"},
    )
    dumped = json.loads(existing.model_dump_json())
    assert dumped["type"] == "existingAgents"
    assert dumped["agents"] == [1, 2]
    assert dumped["agentMeta"]["1"]["palette"] == 0

    # 2. AgentStatus
    status = AgentStatus(id=2, status="active", awaitingInput=False)
    dumped_status = json.loads(status.model_dump_json())
    assert dumped_status["type"] == "agentStatus"
    assert dumped_status["id"] == 2
    assert dumped_status["status"] == "active"

    # 3. AgentToolStart
    tool_start = AgentToolStart(
        id=2,
        toolId="t-1",
        status="Auditing expiry risk",
        toolName="InspectStock",
    )
    dumped_tool = json.loads(tool_start.model_dump_json())
    assert dumped_tool["type"] == "agentToolStart"
    assert dumped_tool["toolName"] == "InspectStock"

    # 4. AgentToolPermission
    perm = AgentToolPermission(id=2)
    assert json.loads(perm.model_dump_json())["type"] == "agentToolPermission"


def test_office_service_workforce():
    """Verify default workforce has 7 agents with CEO as lead."""
    assert len(office_service.agents) == 7
    assert office_service.agents[1].name == "Sarah Chen (CEO)"
    assert office_service.agents[1].is_team_lead is True
    assert office_service.agents[1].seat_id == "seat-ceo"
    assert office_service.agents[2].name == "Marcus Vance (Inventory)"
    assert office_service.agents[2].seat_id == "seat-inventory"
    assert office_service.agents[3].name == "Elena Rostova (Strategy)"
    assert office_service.agents[3].seat_id == "seat-recovery"
    assert office_service.agents[4].name == "David Kim (Logistics)"
    assert office_service.agents[4].seat_id == "seat-logistics"
    assert office_service.agents[5].name == "Aisha Patel (Commerce)"
    assert office_service.agents[5].seat_id == "seat-commerce"
    assert office_service.agents[6].name == "Tom Becker (Fulfillment)"
    assert office_service.agents[6].seat_id == "seat-fulfillment"
    assert office_service.agents[7].name == "Linda Zhang (Finance)"
    assert office_service.agents[7].seat_id == "seat-finance"


def _authenticated_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("RESTOCKAI_DEMO_PASSWORD", "test-suite-pass")
    monkeypatch.setenv("RESTOCKAI_SESSION_SECRET", "test-suite-secret-0123456789abcdef")
    reset_auth_runtime_state()
    c = TestClient(app)
    res = c.post("/api/auth/login", json={"password": "test-suite-pass"})
    assert res.status_code == 200
    c.headers.update({"X-CSRF-Token": res.json()["csrf_token"]})
    return c


def test_office_rest_endpoints(monkeypatch):
    """Test office inspection and test event trigger endpoints."""
    client = _authenticated_client(monkeypatch)

    # 1. GET state
    res = client.get("/api/office/state")
    assert res.status_code == 200
    data = res.json()
    assert "agents" in data
    assert len(data["agents"]) == 7

    # 2. POST update agent status
    res = client.post(
        "/api/office/test/agent-status",
        json={"agent_id": 2, "is_active": True, "awaiting_input": False},
    )
    assert res.status_code == 200
    assert office_service.agents[2].status == "active"

    # 3. POST start tool
    res = client.post(
        "/api/office/test/tool-start",
        json={
            "agent_id": 2,
            "tool_id": "test-tool-1",
            "status": "Inspecting SKU-104",
            "tool_name": "InspectStock",
        },
    )
    assert res.status_code == 200
    assert office_service.agents[2].current_tool is not None

    # 4. POST tool done
    res = client.post(
        "/api/office/test/tool-done",
        json={"agent_id": 2, "tool_id": "test-tool-1"},
    )
    assert res.status_code == 200
    assert office_service.agents[2].current_tool is None

    # 5. POST permission prompt
    res = client.post(
        "/api/office/test/permission",
        json={"agent_id": 2, "required": True},
    )
    assert res.status_code == 200
    assert office_service.agents[2].permission_active is True

    # 6. POST reset
    res = client.post("/api/office/test/reset?agent_id=2")
    assert res.status_code == 200
    assert office_service.agents[2].status == "waiting"
    assert office_service.agents[2].permission_active is False

    # 7. POST simulate sequence
    res = client.post(
        "/api/office/test/simulate-sequence",
        json={
            "agent_id": 2,
            "task_name": "Test Simulation",
            "tool_name": "InspectStock",
            "step_delay_sec": 0.0,
        },
    )
    assert res.status_code == 200
    assert res.json()["status"] == "started"


    # 8. POST agent move destination
    res = client.post(
        "/api/office/agent/move",
        json={"agent_id": 2, "destination": "conference"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.json()["destination"] == "conference"


def test_office_websocket_lifecycle(monkeypatch):
    """Verify WebSocket connection, initial hydration sequence, broadcasting, and reconnection."""
    client = _authenticated_client(monkeypatch)

    with client.websocket_connect("/ws/office") as ws:
        received_types = []
        # Receive hydration sequence messages
        for _ in range(15):
            try:
                raw = ws.receive_text()
                msg = json.loads(raw)
                received_types.append(msg.get("type"))
                if msg.get("type") == "layoutLoaded":
                    break
            except Exception:
                break

        assert "providerCapabilities" in received_types
        assert "existingAgents" in received_types
        assert "agentTeamInfo" in received_types
        assert "layoutLoaded" in received_types

    # Reconnect test: verify fresh connection receives hydration cleanly again
    with client.websocket_connect("/ws/office") as ws2:
        raw_first = ws2.receive_text()
        msg_first = json.loads(raw_first)
        assert msg_first.get("type") == "providerCapabilities"
