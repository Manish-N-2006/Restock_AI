"""
Render Deployment Readiness & PostgreSQL Compatibility Verification Suite.

Tests:
1. Render DATABASE_URL / postgres:// normalization and PostgreSQL engine pooling kwargs.
2. SQLAlchemy PostgreSQL dialect DDL compilation & idempotent seeding (non-destructive).
3. Production CORS origin resolution and CORS preflight headers.
4. Detailed health checks & agent provider health checks.
5. OpenSearch graceful production fallback when OpenSearch is omitted.
6. Production LLM fail-fast (no silent Ollama localhost fallback in production).
7. WebSocket /ws/office hydration + heartbeat ping/pong keepalive.
8. Cedar RBAC identity enforcement and PayPal callback URL resolution.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.auth.service import reset_auth_runtime_state
from app.database import (
    Base,
    SessionLocal,
    get_engine_kwargs,
    is_sqlite_url,
    normalize_database_url,
)
from app.main import app, get_cors_origins
from app.models.store import Store
from app.opensearch.client import get_opensearch_client
from app.opensearch.repository import get_history_summary, search_history
from app.payments.config import _resolve_frontend_callback_url
from app.agent.llm import get_llm_model
from app.services.data_loader import init_db, seed_data


def test_database_url_normalization_and_engine_kwargs():
    render_pg = "postgres://restockuser:s3cr3t@dpg-abc123.oregon-postgres.render.com/restockdb"
    normalized = normalize_database_url(render_pg)
    assert normalized == "postgresql://restockuser:s3cr3t@dpg-abc123.oregon-postgres.render.com/restockdb"
    assert not is_sqlite_url(normalized)

    pg_kwargs = get_engine_kwargs(normalized)
    assert "check_same_thread" not in pg_kwargs.get("connect_args", {})
    assert pg_kwargs["pool_pre_ping"] is True
    assert pg_kwargs["pool_recycle"] == 300

    sqlite_url = "sqlite:///./restock.db"
    assert is_sqlite_url(sqlite_url)
    sqlite_kwargs = get_engine_kwargs(sqlite_url)
    assert sqlite_kwargs == {"connect_args": {"check_same_thread": False}}


def test_postgresql_dialect_ddl_compilation():
    import app.models  # noqa: F401

    dialect = postgresql.dialect()
    table_names = set(Base.metadata.tables.keys())
    expected_tables = {
        "stores",
        "logistics_partners",
        "inventory",
        "transfer_orders",
        "transfer_events",
        "outcomes",
        "outcome_events",
        "recovery_orders",
        "recovery_offers",
        "payment_transactions",
        "revoked_sessions",
        "login_attempt_buckets",
    }
    assert expected_tables.issubset(table_names)

    for tbl in Base.metadata.sorted_tables:
        ddl = str(CreateTable(tbl).compile(dialect=dialect))
        assert f"CREATE TABLE {tbl.name}" in ddl


def test_alembic_initial_migration_fresh_db_and_offline_postgres():
    repo_root = Path(__file__).resolve().parents[2]
    alembic_ini = repo_root / "backend" / "alembic.ini"
    assert alembic_ini.exists()

    # 1. Verify offline PostgreSQL DDL generation via Alembic CLI
    env_pg = os.environ.copy()
    env_pg["ALEMBIC_OFFLINE_URL"] = "postgresql://user:pass@localhost:5432/restockai"
    res_sql = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "upgrade", "head", "--sql"],
        cwd=str(repo_root),
        env=env_pg,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res_sql.returncode == 0, res_sql.stderr
    assert "CREATE TABLE payment_transactions" in res_sql.stdout
    assert "CREATE TABLE revoked_sessions" in res_sql.stdout
    assert "CREATE TABLE login_attempt_buckets" in res_sql.stdout
    assert "CREATE TYPE transferstatus AS ENUM" in res_sql.stdout

    # 2. Verify online migration execution on a clean temporary database
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_db = os.path.join(tmpdir, "alembic_test.db").replace("\\", "/")
        env_sqlite = os.environ.copy()
        env_sqlite["RESTOCKAI_DATABASE_URL"] = f"sqlite:///{temp_db}"
        res_up = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "upgrade", "head"],
            cwd=str(repo_root),
            env=env_sqlite,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert res_up.returncode == 0, res_up.stderr

        check_eng = create_engine(f"sqlite:///{temp_db}")
        insp = inspect(check_eng)
        tables = set(insp.get_table_names())
        assert "alembic_version" in tables
        assert "stores" in tables
        assert "payment_transactions" in tables
        assert "revoked_sessions" in tables
        assert "login_attempt_buckets" in tables
        check_eng.dispose()


def test_seed_data_is_non_destructive():
    init_db()
    seed_data()
    with SessionLocal() as db:
        initial_count = db.query(Store).count()
        assert initial_count >= 5

        first_store = db.query(Store).first()
        first_id = first_store.id
        original_name = first_store.store_name
        first_store.store_name = "Modified Branch Persist Check"
        db.commit()

    # Re-running init_db + seed_data must never overwrite or duplicate records
    init_db()
    seed_data()

    with SessionLocal() as db:
        assert db.query(Store).count() == initial_count
        refetched = db.query(Store).filter(Store.id == first_id).first()
        assert refetched is not None
        assert refetched.store_name == "Modified Branch Persist Check"
        # Restore original seeded name
        refetched.store_name = original_name
        db.commit()


def test_production_cors_and_paypal_callback_resolution(monkeypatch):
    monkeypatch.setenv("RESTOCKAI_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", "https://restockai-web.onrender.com/")
    monkeypatch.setenv("CORS_ORIGINS", "https://custom.restockai.io, https://restockai-web.onrender.com")

    origins = get_cors_origins()
    assert origins == [
        "https://custom.restockai.io",
        "https://restockai-web.onrender.com",
    ]
    assert all("localhost" not in o for o in origins)

    monkeypatch.delenv("PAYPAL_RETURN_URL", raising=False)
    monkeypatch.delenv("PAYPAL_CANCEL_URL", raising=False)
    assert _resolve_frontend_callback_url("PAYPAL_RETURN_URL", "/checkout/success") == "https://restockai-web.onrender.com/checkout/success"
    assert _resolve_frontend_callback_url("PAYPAL_CANCEL_URL", "/checkout/cancel") == "https://restockai-web.onrender.com/checkout/cancel"


def test_health_details_and_provider_health(monkeypatch):
    client = TestClient(app)

    res_basic = client.get("/health")
    assert res_basic.status_code == 200
    assert res_basic.json() == {"status": "ok", "service": "ReStockAI"}

    # Detailed telemetry requires authenticated demo session
    assert client.get("/health/details").status_code == 401

    monkeypatch.setenv("RESTOCKAI_DEMO_PASSWORD", "test-suite-pass")
    monkeypatch.setenv("RESTOCKAI_SESSION_SECRET", "test-suite-secret-0123456789abcdef")
    reset_auth_runtime_state()
    assert client.post("/api/auth/login", json={"password": "test-suite-pass"}).status_code == 200

    res_det = client.get("/health/details")
    assert res_det.status_code == 200
    det = res_det.json()
    assert det["status"] == "ok"
    assert det["database"]["connected"] is True
    assert det["database"]["dialect"] in ("sqlite", "postgresql")

    monkeypatch.setenv("RESTOCKAI_LLM_PROVIDER", "groq")
    monkeypatch.setenv("RESTOCKAI_GROQ_API_KEY", "gsk_dummy_render_check")
    res_llm = client.get("/api/agent/provider-health")
    assert res_llm.status_code == 200
    llm_data = res_llm.json()
    assert llm_data["model_provider"] == "groq"
    assert llm_data["configured"] is True


def test_production_groq_missing_key_fails_fast(monkeypatch):
    monkeypatch.setenv("RESTOCKAI_ENV", "production")
    monkeypatch.setenv("RESTOCKAI_LLM_PROVIDER", "groq")
    monkeypatch.delenv("RESTOCKAI_GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ValueError, match="RESTOCKAI_GROQ_API_KEY is required in production"):
        get_llm_model()


def test_opensearch_disabled_in_production_and_falls_back_to_sql(monkeypatch):
    monkeypatch.setenv("RESTOCKAI_ENV", "production")
    monkeypatch.delenv("RESTOCKAI_OPENSEARCH_HOST", raising=False)
    monkeypatch.setenv("RESTOCKAI_OPENSEARCH_FALLBACK", "true")

    assert get_opensearch_client() is None

    search_res = search_history(q="Yogurt")
    assert "error" not in search_res
    assert isinstance(search_res["results"], list)

    summary_res = get_history_summary()
    assert "error" not in summary_res
    assert "total_indexed_transfers" in summary_res


def test_websocket_office_hydration_and_ping_pong(monkeypatch):
    monkeypatch.setenv("RESTOCKAI_DEMO_PASSWORD", "test-suite-pass")
    monkeypatch.setenv("RESTOCKAI_SESSION_SECRET", "test-suite-secret-0123456789abcdef")
    reset_auth_runtime_state()
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"password": "test-suite-pass"}).status_code == 200
    with client.websocket_connect("/ws/office") as ws:
        # Drain initial connect hydration until settingsLoaded
        received_types = set()
        for _ in range(25):
            raw = ws.receive_text()
            msg = json.loads(raw)
            received_types.add(msg.get("type"))
            if msg.get("type") == "settingsLoaded":
                break

        assert "layoutLoaded" in received_types
        assert "existingAgents" in received_types

        # Test heartbeat keepalive for Render proxy timeout resilience
        ws.send_text(json.dumps({"type": "ping"}))
        pong_msg = json.loads(ws.receive_text())
        assert pong_msg["type"] == "pong"
        assert isinstance(pong_msg["timestamp"], float)


def test_authorization_missing_header_vs_manager_header(monkeypatch):
    # Verify unauthenticated requests and forged X-ReStockAI-User headers are rejected with 401,
    # while authenticated sessions receive server-assigned MANAGER identity.
    saved_overrides = dict(app.dependency_overrides)
    app.dependency_overrides.clear()
    monkeypatch.setenv("RESTOCKAI_DEMO_PASSWORD", "test-suite-pass")
    monkeypatch.setenv("RESTOCKAI_SESSION_SECRET", "test-suite-secret-0123456789abcdef")
    reset_auth_runtime_state()
    try:
        client = TestClient(app)
        res_unauth = client.get("/api/risk")
        assert res_unauth.status_code == 401

        res_forged = client.get("/api/risk", headers={"X-ReStockAI-User": "manager"})
        assert res_forged.status_code == 401

        assert client.post("/api/auth/login", json={"password": "test-suite-pass"}).status_code == 200
        res_mgr = client.get("/api/risk")
        assert res_mgr.status_code == 200
    finally:
        app.dependency_overrides.update(saved_overrides)
