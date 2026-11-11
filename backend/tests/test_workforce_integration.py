import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.service import reset_auth_runtime_state
from app.agent.workforce import (
    run_workforce_recovery_orchestration,
    execute_inventory_agent,
    execute_recovery_strategy_agent,
    execute_logistics_agent,
    pending_approvals,
    CEOOpsReport,
    InventoryAgentResult,
    RecoveryStrategyResult,
    LogisticsAgentResult,
)
from app.agent.llm import get_llm_model, DEFAULT_GROQ_MODEL
from app.office.service import office_service
from app.authorization.actions import Action
from app.authorization.entities import build_user_entity


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RESTOCKAI_DEMO_PASSWORD", "test-suite-pass")
    monkeypatch.setenv("RESTOCKAI_SESSION_SECRET", "test-suite-secret-0123456789abcdef")
    reset_auth_runtime_state()
    c = TestClient(app)
    res = c.post("/api/auth/login", json={"password": "test-suite-pass"})
    assert res.status_code == 200
    c.headers.update({"X-CSRF-Token": res.json()["csrf_token"]})
    return c


@pytest.mark.asyncio
async def test_inventory_agent_execution():
    """Verify Inventory Agent executes real risk_engine and returns structured result."""
    result = await execute_inventory_agent(sku_id="YOG-001", store_id="STORE_A")
    assert isinstance(result, InventoryAgentResult)
    assert result.agent_id == 2
    assert result.sku_id == "YOG-001"
    assert result.store_id == "STORE_A"
    assert result.product_name == "Yogurt 500g"
    assert result.quantity > 0
    assert result.risk_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert len(result.recommendation_summary) > 0


@pytest.mark.asyncio
async def test_recovery_strategy_agent_execution():
    """Verify Recovery Strategy Agent executes real decision_engine and demand_engine."""
    result = await execute_recovery_strategy_agent(sku_id="YOG-001", source_store_id="STORE_A")
    assert isinstance(result, RecoveryStrategyResult)
    assert result.agent_id == 3
    assert result.sku_id == "YOG-001"
    assert result.selected_action in (
        "TRANSFER", "DISCOUNT", "PROMOTE", "BUNDLE", "RETURN", "DISPOSE", "NO_ACTION"
    )
    assert result.candidate_destinations_count >= 0


@pytest.mark.asyncio
async def test_logistics_agent_execution():
    """Verify Logistics Agent executes real logistics_engine."""
    result = await execute_logistics_agent(sku_id="YOG-001", source_store_id="STORE_A")
    assert isinstance(result, LogisticsAgentResult)
    assert result.agent_id == 4
    assert result.sku_id == "YOG-001"
    assert result.source_store_id == "STORE_A"
    assert isinstance(result.transfer_viable, bool)
    assert isinstance(result.distance_km, float)


@pytest.mark.asyncio
async def test_ceo_orchestration_workflow():
    """Verify full multi-agent orchestration: CEO -> Inventory -> Recovery -> Logistics -> CEOOpsReport."""
    report = await run_workforce_recovery_orchestration(
        sku_id="YOG-001",
        source_store_id="STORE_A",
        auto_approve=True,  # Test auto-approve path
    )
    assert isinstance(report, CEOOpsReport)
    assert report.sku_id == "YOG-001"
    assert report.source_store_id == "STORE_A"
    assert report.product_name == "Yogurt 500g"
    assert report.inventory_findings is not None
    assert report.inventory_findings.agent_id == 2
    assert len(report.timeline) >= 3
    assert report.overall_status in ("COMPLETED", "NO_ACTION_REQUIRED")


@pytest.mark.asyncio
async def test_human_approval_pause_and_resume(client):
    """Verify that transfers requiring approval pause the workflow and resume via decision endpoint."""
    # 1. Trigger workflow without auto_approve
    res = client.post("/api/office/workflow/trigger", json={
        "sku_id": "YOG-001",
        "source_store_id": "STORE_A",
        "auto_approve": False,
    })
    assert res.status_code == 200
    report_data = res.json()

    if report_data["requires_human_approval"]:
        approval_id = report_data["approval_id"]
        assert approval_id is not None
        assert report_data["overall_status"] == "PENDING_APPROVAL"

        # 2. Check pending approvals list
        pending_res = client.get("/api/office/approval/pending")
        assert pending_res.status_code == 200
        pending_data = pending_res.json()
        assert any(a["approval_id"] == approval_id for a in pending_data["approvals"])

        # 3. Submit Manager Approval
        decision_res = client.post("/api/office/approval/decision", json={
            "approval_id": approval_id,
            "decision": "APPROVED",
            "approver": "ops-manager-1",
            "notes": "Transfer authorized based on net recovery and cold-chain compliance",
        })
        assert decision_res.status_code == 200
        decision_data = decision_res.json()
        assert decision_data["status"] == "ok"
        assert decision_data["decision"] == "APPROVED"
        assert decision_data["approver"] == "ops-manager-1"

        # 4. Confirm permission prompt on Logistics Agent is cleared
        assert office_service.agents[4].permission_active is False


def test_production_guards_on_test_endpoints(monkeypatch):
    """Verify authenticated office /test/* endpoints return 403 Forbidden in production."""
    monkeypatch.setenv("RESTOCKAI_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", "https://restockai-web.onrender.com")
    monkeypatch.setenv("RESTOCKAI_DEMO_PASSWORD", "test-suite-pass")
    monkeypatch.setenv("RESTOCKAI_SESSION_SECRET", "test-suite-secret-0123456789abcdef")
    reset_auth_runtime_state()

    prod_client = TestClient(app, base_url="https://restockai-api.onrender.com")
    login_res = prod_client.post(
        "/api/auth/login",
        headers={"Origin": "https://restockai-web.onrender.com"},
        json={"password": "test-suite-pass"},
    )
    assert login_res.status_code == 200
    csrf = login_res.json()["csrf_token"]

    res = prod_client.post(
        "/api/office/test/simulate-sequence",
        headers={
            "Origin": "https://restockai-web.onrender.com",
            "X-CSRF-Token": csrf,
        },
        json={
            "agent_id": 2,
            "task_name": "Test Simulation",
            "tool_name": "InspectStock",
            "step_delay_sec": 0.0,
        },
    )
    assert res.status_code == 403
    assert "disabled outside development environments" in res.json()["detail"]


def test_groq_llm_factory_configuration(monkeypatch):
    """Verify get_llm_model configures OpenAIModel with Groq endpoints and fallback correctly."""
    # 1. With Groq API Key
    monkeypatch.setenv("RESTOCKAI_LLM_PROVIDER", "groq")
    monkeypatch.setenv("RESTOCKAI_GROQ_API_KEY", "gsk_test_mock_key_12345")
    monkeypatch.setenv("RESTOCKAI_AGENT_MODEL", "llama-3.3-70b-versatile")

    model = get_llm_model()
    assert hasattr(model, "client_args")
    assert model.client_args.get("base_url") == "https://api.groq.com/openai/v1"
    assert model.client_args.get("api_key") == "gsk_test_mock_key_12345"

    # 2. Ollama explicit configuration
    monkeypatch.setenv("RESTOCKAI_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("RESTOCKAI_AGENT_MODEL", "llama3.1")
    ollama_model = get_llm_model()
    assert ollama_model.config.get("model_id") == "llama3.1"
    assert ollama_model.host == "http://localhost:11434"
