import json
import time
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient
import pytest

from app.auth.models import LoginAttemptBucket, RevokedSession
from app.auth.service import (
    DEFAULT_SESSION_COOKIE_NAME,
    HOST_SESSION_COOKIE_NAME,
    create_session_token,
    get_session_ttl_minutes,
    reset_auth_runtime_state,
    validate_production_configuration,
    validate_session_secret,
)
from app.database import SessionLocal
from app.main import app, create_app, get_cors_origin_regex, get_cors_origins
from app.office.service import office_service
from app.payments.config import _resolve_frontend_callback_url


TEST_DEMO_PASSWORD = "pytest-demo-pass-!9xQ"
TEST_SESSION_SECRET = "pytest-signing-secret-0123456789abcdef0123456789"
PROD_FRONTEND_URL = "https://restockai-web.onrender.com"


@pytest.fixture(autouse=True)
def isolated_auth_env(monkeypatch):
    """Ensure clean persisted auth state, env config, and zero leaked dependency overrides."""
    saved_overrides = dict(app.dependency_overrides)
    app.dependency_overrides.clear()
    reset_auth_runtime_state()

    monkeypatch.setenv("RESTOCKAI_ENV", "test")
    monkeypatch.setenv("RESTOCKAI_DEMO_PASSWORD", TEST_DEMO_PASSWORD)
    monkeypatch.setenv("RESTOCKAI_SESSION_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("RESTOCKAI_SESSION_TTL_MINUTES", "60")
    monkeypatch.setenv("RESTOCKAI_TRUSTED_PROXY_HOPS", "0")
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved_overrides)
        reset_auth_runtime_state()


def _login_client(
    client: TestClient,
    password: str = TEST_DEMO_PASSWORD,
    origin: str | None = None,
    headers: dict | None = None,
):
    req_headers = dict(headers or {})
    if origin is not None:
        req_headers["Origin"] = origin
    return client.post("/api/auth/login", json={"password": password}, headers=req_headers)


# ==============================================================================
# Core Demo Authentication Suite (Phase 1)
# ==============================================================================

def test_unauthenticated_api_request_rejected():
    """Unauthenticated requests across all protected operational routes must return 401."""
    client = TestClient(app)
    assert client.get("/health").status_code == 200

    protected_gets = [
        "/health/details",
        "/api/health",
        "/api/inventory",
        "/api/risk",
        "/api/risk/summary",
        "/api/demand/summary",
        "/api/decision/summary",
        "/api/logistics/summary",
        "/api/transfers/",
        "/api/outcomes/summary",
        "/api/history/summary",
        "/api/workflow/status/TR-1",
        "/api/agent/health",
        "/api/office/state",
        "/api/auth/session",
    ]
    for path in protected_gets:
        res = client.get(path)
        assert res.status_code == 401, f"Expected 401 on GET {path}, got {res.status_code}"

    protected_posts = [
        ("/api/recovery/evaluate", {"sku_id": "YOG-001", "quantity": 5, "source_store_id": "STORE_A", "action": "transfer"}),
        ("/api/workflow/analyze", {"sku_id": "YOG-001", "source_store_id": "STORE_A"}),
        ("/api/authorization/check", {"action": "CREATE_TRANSFER", "resource_type": "Transfer", "resource_id": "tr-1"}),
        ("/api/agent/ask", {"question": "Status?"}),
    ]
    for path, body in protected_posts:
        res = client.post(path, json=body)
        assert res.status_code == 401, f"Expected 401 on POST {path}, got {res.status_code}"


def test_incorrect_demo_password_rejected():
    """Wrong demo password must return 401 and issue no session cookie."""
    client = TestClient(app)
    res = _login_client(client, password="definitely-wrong-password")
    assert res.status_code == 401
    assert DEFAULT_SESSION_COOKIE_NAME not in client.cookies
    assert HOST_SESSION_COOKIE_NAME not in client.cookies


def test_login_rate_limiting_blocks_brute_force(monkeypatch):
    """Brute-force login attempts return HTTP 429 with Retry-After header."""
    monkeypatch.setenv("RESTOCKAI_LOGIN_MAX_ATTEMPTS", "5")
    client = TestClient(app)

    for _ in range(5):
        assert _login_client(client, password="wrong-password").status_code == 401

    blocked = _login_client(client, password=TEST_DEMO_PASSWORD)
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_correct_password_creates_valid_session_and_manager_principal():
    """Valid password issues HttpOnly cookie, session-bound CSRF token, and MANAGER principal."""
    client = TestClient(app)
    res = _login_client(client)
    assert res.status_code == 200
    body = res.json()
    assert body["authenticated"] is True
    assert body["role"] == "MANAGER"
    assert body["csrf_token"]
    assert DEFAULT_SESSION_COOKIE_NAME in client.cookies
    assert "httponly" in res.headers.get("set-cookie", "").lower()

    csrf_token = body["csrf_token"]
    session_res = client.get("/api/auth/session")
    assert session_res.status_code == 200
    assert session_res.json()["csrf_token"] == csrf_token

    assert client.get("/api/risk").status_code == 200

    authz_res = client.post(
        "/api/authorization/check",
        headers={"X-CSRF-Token": csrf_token},
        json={"action": "CREATE_TRANSFER", "resource_type": "Transfer", "resource_id": "tr-1"},
    )
    assert authz_res.status_code == 200
    assert authz_res.json()["principal_role"] == "MANAGER"
    assert authz_res.json()["allowed"] is True


def test_expired_session_rejected():
    """Expired session tokens must be rejected across HTTP, session, and WS endpoints."""
    expired_token, _ = create_session_token(ttl_seconds=-30)
    client = TestClient(app)
    client.cookies.set(DEFAULT_SESSION_COOKIE_NAME, expired_token)

    assert client.get("/api/auth/session").status_code == 401
    assert client.get("/api/risk").status_code == 401
    assert client.get("/api/payments/orders/eligible").status_code == 401

    with pytest.raises((WebSocketDisconnect, Exception)):
        with client.websocket_connect("/ws/office") as ws:
            ws.receive_text()


def test_forged_header_cannot_impersonate_manager():
    """Client-supplied X-ReStockAI-User header must never authenticate or elevate privilege."""
    client = TestClient(app)
    forged_headers = {"X-ReStockAI-User": "manager"}

    assert client.get("/api/risk", headers=forged_headers).status_code == 401
    assert client.post(
        "/api/authorization/check",
        headers=forged_headers,
        json={"action": "CREATE_TRANSFER", "resource_type": "Transfer", "resource_id": "tr-1"},
    ).status_code == 401
    assert client.post(
        "/api/transfers/",
        headers=forged_headers,
        json={
            "sku_id": "YOG-001",
            "source_store_id": "STORE_A",
            "destination_store_id": "STORE_B",
            "quantity": 5,
        },
    ).status_code == 401


def test_unauthenticated_simulation_and_payment_requests_rejected():
    """All simulation and payment inspection/mutation routes must reject unauthenticated callers."""
    client = TestClient(app)
    assert client.get("/api/simulation/state").status_code == 401
    assert client.post("/api/simulation/reset", json={"scenario_type": "SCENARIO_A"}).status_code == 401
    assert client.post("/api/simulation/step?run_id=fake").status_code == 401
    assert client.post("/api/simulation/approve", json={"run_id": "fake", "decision": "APPROVED"}).status_code == 401
    assert client.get("/api/payments/config").status_code == 401
    assert client.get("/api/payments/orders/eligible").status_code == 401
    assert client.post("/api/payments/paypal/create-order", json={"recovery_order_id": "ORD-1"}).status_code == 401
    assert client.post(
        "/api/payments/paypal/capture",
        json={"paypal_order_id": "PP-1", "recovery_order_id": "ORD-1"},
    ).status_code == 401


def test_unauthenticated_and_authenticated_websocket():
    """Unauthenticated WebSocket upgrades close cleanly; authenticated WebSockets hydrate."""
    client = TestClient(app)
    for ws_path in ("/ws/office", "/ws"):
        with pytest.raises((WebSocketDisconnect, Exception)):
            with client.websocket_connect(ws_path) as ws:
                ws.receive_text()

    assert _login_client(client).status_code == 200
    with client.websocket_connect("/ws/office") as ws:
        received_types = set()
        for _ in range(25):
            msg = json.loads(ws.receive_text())
            received_types.add(msg.get("type"))
            if msg.get("type") == "settingsLoaded":
                break
        assert "existingAgents" in received_types
        assert "layoutLoaded" in received_types
        ws.send_text(json.dumps({"type": "ping"}))
        assert json.loads(ws.receive_text())["type"] == "pong"


def test_missing_auth_configuration_fails_closed(monkeypatch):
    """Server returns HTTP 503 if demo password is missing."""
    monkeypatch.delenv("RESTOCKAI_DEMO_PASSWORD", raising=False)
    client = TestClient(app)
    assert _login_client(client, password="any").status_code == 503


# ==============================================================================
# Phase 2 Production Security Hardening Tests (Checklist 1..17)
# ==============================================================================

def test_1_cross_origin_mutation_request_rejected():
    """1. Cross-origin POST/PUT/PATCH/DELETE requests from untrusted Origin must be rejected (403)."""
    client = TestClient(app)
    login_res = _login_client(client)
    csrf = login_res.json()["csrf_token"]

    res = client.post(
        "/api/simulation/reset",
        headers={"Origin": "https://attacker.example", "X-CSRF-Token": csrf},
        json={"scenario_type": "SCENARIO_A"},
    )
    assert res.status_code == 403
    assert "origin" in res.json()["detail"].lower()

    # Cross-origin login & logout also rejected
    assert _login_client(client, origin="https://attacker.example").status_code == 403
    assert client.post(
        "/api/auth/logout",
        headers={"Origin": "https://attacker.example", "X-CSRF-Token": csrf},
    ).status_code == 403


def test_2_missing_origin_rejected_in_production(monkeypatch):
    """2. Missing Origin header on state-changing requests is rejected with 403 in production."""
    monkeypatch.setenv("RESTOCKAI_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", PROD_FRONTEND_URL)
    prod_client = TestClient(app, base_url="https://restockai-api.onrender.com")

    # Login without Origin in production must return 403
    assert _login_client(prod_client).status_code == 403

    # Authenticate with valid Origin, then call mutation without Origin -> must return 403
    login_res = _login_client(prod_client, origin=PROD_FRONTEND_URL)
    assert login_res.status_code == 200
    csrf = login_res.json()["csrf_token"]

    missing_origin_res = prod_client.post(
        "/api/simulation/reset",
        headers={"X-CSRF-Token": csrf},
        json={"scenario_type": "SCENARIO_A"},
    )
    assert missing_origin_res.status_code == 403
    assert "Origin header is required" in missing_origin_res.json()["detail"]


def test_3_invalid_csrf_token_and_non_json_rejected():
    """3. Missing/wrong/foreign CSRF tokens return 403, and form/text payloads return 415."""
    client_a = TestClient(app)
    login_a = _login_client(client_a)
    csrf_a = login_a.json()["csrf_token"]

    client_b = TestClient(app)
    _login_client(client_b)

    # Missing X-CSRF-Token
    assert client_a.post("/api/simulation/reset", json={"scenario_type": "SCENARIO_A"}).status_code == 403
    # Wrong X-CSRF-Token
    assert client_a.post(
        "/api/simulation/reset",
        headers={"X-CSRF-Token": "wrong-csrf-token"},
        json={"scenario_type": "SCENARIO_A"},
    ).status_code == 403
    # Session A's CSRF token cannot authorize Session B
    assert client_b.post(
        "/api/simulation/reset",
        headers={"X-CSRF-Token": csrf_a},
        json={"scenario_type": "SCENARIO_A"},
    ).status_code == 403
    # Active logout without valid CSRF token is rejected (403)
    assert client_a.post("/api/auth/logout").status_code == 403
    # HTML form / text/plain mutation is rejected (415)
    assert client_a.post(
        "/api/simulation/reset",
        headers={"X-CSRF-Token": csrf_a, "Content-Type": "text/plain"},
        content='{"scenario_type": "SCENARIO_A"}',
    ).status_code == 415


def test_4_and_5_valid_csrf_and_frontend_origin_mutation_succeeds(monkeypatch):
    """4 & 5. Production HTTPS __Host- cookie, valid Origin, and valid CSRF allow mutation."""
    monkeypatch.setenv("RESTOCKAI_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", PROD_FRONTEND_URL)
    prod_app = create_app()
    prod_client = TestClient(prod_app, base_url="https://restockai-api.onrender.com")

    assert get_cors_origins() == [PROD_FRONTEND_URL]
    assert get_cors_origin_regex() is None

    login_res = _login_client(prod_client, origin=PROD_FRONTEND_URL)
    assert login_res.status_code == 200
    cookie_hdr = login_res.headers.get("set-cookie", "").lower()
    assert f"{HOST_SESSION_COOKIE_NAME.lower()}=" in cookie_hdr
    assert "httponly" in cookie_hdr
    assert "secure" in cookie_hdr
    assert "samesite=none" in cookie_hdr
    assert "domain=" not in cookie_hdr

    csrf = login_res.json()["csrf_token"]
    mut_res = prod_client.post(
        "/api/simulation/reset",
        headers={"Origin": PROD_FRONTEND_URL, "X-CSRF-Token": csrf},
        json={"scenario_type": "SCENARIO_A"},
    )
    assert mut_res.status_code == 200
    assert mut_res.json()["scenario_id"] == "SCENARIO_A"


def test_6_untrusted_and_missing_websocket_origin_rejected(monkeypatch):
    """6. Untrusted WebSocket Origin (and missing Origin in production) are rejected with 1008."""
    client = TestClient(app)
    assert _login_client(client).status_code == 200

    with pytest.raises((WebSocketDisconnect, Exception)):
        with client.websocket_connect("/ws/office", headers={"Origin": "https://evil.example"}) as ws:
            ws.receive_text()

    monkeypatch.setenv("RESTOCKAI_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", PROD_FRONTEND_URL)
    prod_client = TestClient(app, base_url="https://restockai-api.onrender.com")
    assert _login_client(prod_client, origin=PROD_FRONTEND_URL).status_code == 200

    # Missing Origin on production WS handshake rejected
    with pytest.raises((WebSocketDisconnect, Exception)):
        with prod_client.websocket_connect("/ws/office") as ws:
            ws.receive_text()

    # Untrusted Origin on production WS handshake rejected
    with pytest.raises((WebSocketDisconnect, Exception)):
        with prod_client.websocket_connect("/ws/office", headers={"Origin": "https://other.onrender.com"}) as ws:
            ws.receive_text()


def test_7_valid_websocket_origin_accepted(monkeypatch):
    """7. Authenticated WebSocket handshake matching FRONTEND_URL Origin succeeds in production."""
    monkeypatch.setenv("RESTOCKAI_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", PROD_FRONTEND_URL)
    prod_client = TestClient(app, base_url="https://restockai-api.onrender.com")
    login_res = _login_client(prod_client, origin=PROD_FRONTEND_URL)
    assert login_res.status_code == 200

    # Python http.cookiejar omits Secure cookies on wss:// URLs even when base_url is https://,
    # so pass the issued __Host- cookie explicitly just as browsers do on wss:// upgrades.
    host_cookie = prod_client.cookies.get(HOST_SESSION_COOKIE_NAME)
    assert host_cookie
    with prod_client.websocket_connect(
        "/ws/office",
        headers={
            "Origin": PROD_FRONTEND_URL,
            "Cookie": f"{HOST_SESSION_COOKIE_NAME}={host_cookie}",
        },
    ) as ws:
        ws.send_text(json.dumps({"type": "ping"}))
        seen_pong = False
        for _ in range(30):
            msg = json.loads(ws.receive_text())
            if msg.get("type") == "pong":
                seen_pong = True
                break
        assert seen_pong is True


def test_8_spoofed_x_forwarded_for_cannot_bypass_rate_limiting(monkeypatch):
    """8. Rotating fake leftmost X-Forwarded-For values cannot bypass rate limiting."""
    monkeypatch.setenv("RESTOCKAI_LOGIN_MAX_ATTEMPTS", "5")
    monkeypatch.setenv("RESTOCKAI_TRUSTED_PROXY_HOPS", "1")
    client = TestClient(app)

    # Simulate client spoofing leftmost IP while Render edge proxy appends consistent rightmost real IP
    for idx in range(5):
        res = _login_client(
            client,
            password="wrong-password",
            headers={"X-Forwarded-For": f"198.51.100.{idx + 1}, 203.0.113.42"},
        )
        assert res.status_code == 401

    blocked = _login_client(
        client,
        password=TEST_DEMO_PASSWORD,
        headers={"X-Forwarded-For": "192.0.2.99, 203.0.113.42"},
    )
    assert blocked.status_code == 429

    # When RESTOCKAI_TRUSTED_PROXY_HOPS=0, arbitrary X-Forwarded-For headers are ignored completely
    reset_auth_runtime_state()
    monkeypatch.setenv("RESTOCKAI_TRUSTED_PROXY_HOPS", "0")
    for idx in range(5):
        assert _login_client(
            client,
            password="wrong-password",
            headers={"X-Forwarded-For": f"10.0.0.{idx + 1}"},
        ).status_code == 401
    assert _login_client(client, password=TEST_DEMO_PASSWORD).status_code == 429


def test_9_expired_login_attempt_entries_cleaned_up(monkeypatch):
    """9. Expired failed-login bucket rows are pruned automatically from persistence."""
    now = time.time()
    with SessionLocal() as db:
        db.add(
            LoginAttemptBucket(
                bucket_key="ip:198.51.100.77",
                attempt_timestamps=json.dumps([now - 900]),
                window_expires_at=now - 10,
                updated_at=now - 900,
            )
        )
        db.commit()

    client = TestClient(app)
    assert _login_client(client, password="wrong-password").status_code == 401

    with SessionLocal() as db:
        stale = db.query(LoginAttemptBucket).filter(LoginAttemptBucket.bucket_key == "ip:198.51.100.77").first()
        assert stale is None


def test_10_rate_limit_state_survives_restart(monkeypatch):
    """10. Persisted failed-login counters continue blocking after rebuilding the FastAPI app."""
    monkeypatch.setenv("RESTOCKAI_LOGIN_MAX_ATTEMPTS", "5")
    client_before = TestClient(create_app())
    for _ in range(5):
        assert _login_client(client_before, password="wrong-password").status_code == 401

    # Fresh app instance simulating container restart/wake
    client_after = TestClient(create_app())
    res_after = _login_client(client_after, password=TEST_DEMO_PASSWORD)
    assert res_after.status_code == 429
    assert "Retry-After" in res_after.headers


def test_11_weak_session_secret_rejected(monkeypatch):
    """11. Short secrets (< 32 chars) and secrets matching RESTOCKAI_DEMO_PASSWORD are rejected."""
    monkeypatch.setenv("RESTOCKAI_SESSION_SECRET", "short-secret")
    with pytest.raises(ValueError, match="at least 32 characters"):
        validate_session_secret()
    assert _login_client(TestClient(app)).status_code == 503

    monkeypatch.setenv("RESTOCKAI_DEMO_PASSWORD", "A" * 40)
    monkeypatch.setenv("RESTOCKAI_SESSION_SECRET", "A" * 40)
    with pytest.raises(ValueError, match="must not match RESTOCKAI_DEMO_PASSWORD"):
        validate_session_secret()
    assert _login_client(TestClient(app), password="A" * 40).status_code == 503


def test_12_excessive_session_ttl_rejected(monkeypatch):
    """12. Session TTL > 480 minutes or < 1 minute must be rejected."""
    monkeypatch.setenv("RESTOCKAI_SESSION_TTL_MINUTES", "481")
    with pytest.raises(ValueError, match="between 1 and 480"):
        get_session_ttl_minutes()
    assert _login_client(TestClient(app)).status_code == 503

    monkeypatch.setenv("RESTOCKAI_SESSION_TTL_MINUTES", "0")
    with pytest.raises(ValueError, match="between 1 and 480"):
        get_session_ttl_minutes()


def test_13_revoked_sessions_remain_revoked_after_restart():
    """13. Logged-out session JTI persists in DB and stays rejected across app restarts."""
    client_1 = TestClient(create_app())
    login_res = _login_client(client_1)
    assert login_res.status_code == 200
    csrf = login_res.json()["csrf_token"]
    old_cookie = client_1.cookies.get(DEFAULT_SESSION_COOKIE_NAME)
    assert old_cookie

    logout_res = client_1.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logout_res.status_code == 200

    with SessionLocal() as db:
        assert db.query(RevokedSession).count() >= 1

    # Fresh app instance simulating restart
    replay_client = TestClient(create_app())
    replay_client.cookies.set(DEFAULT_SESSION_COOKIE_NAME, old_cookie)
    assert replay_client.get("/api/auth/session").status_code == 401
    assert replay_client.get("/api/risk").status_code == 401


def test_14_logged_out_websockets_are_closed():
    """14. Logging out actively closes live WebSocket connections bound to that session JTI."""
    client = TestClient(app)
    login_res = _login_client(client)
    assert login_res.status_code == 200
    csrf = login_res.json()["csrf_token"]

    with client.websocket_connect("/ws/office") as ws:
        # Drain full initial hydration until settingsLoaded so receive queue is clear
        for _ in range(30):
            msg = json.loads(ws.receive_text())
            if msg.get("type") == "settingsLoaded":
                break
        assert len(office_service.websocket_sessions) >= 1

        logout_res = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
        assert logout_res.status_code == 200

        with pytest.raises(WebSocketDisconnect) as exc_info:
            for _ in range(10):
                ws.receive_text()
        assert exc_info.value.code == 1008


def test_15_swagger_openapi_disabled_in_production(monkeypatch):
    """15. /docs, /redoc, and /openapi.json must return 404 when RESTOCKAI_ENV=production."""
    monkeypatch.setenv("RESTOCKAI_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", PROD_FRONTEND_URL)
    validate_production_configuration()

    prod_client = TestClient(create_app(), base_url="https://restockai-api.onrender.com")
    assert prod_client.get("/docs").status_code == 404
    assert prod_client.get("/redoc").status_code == 404
    assert prod_client.get("/openapi.json").status_code == 404
    # Health check remains public
    assert prod_client.get("/health").status_code == 200


def test_16_local_swagger_openapi_works_in_development(monkeypatch):
    """16. Developer API documentation remains accessible in development."""
    monkeypatch.setenv("RESTOCKAI_ENV", "development")
    dev_client = TestClient(create_app())
    assert dev_client.get("/docs").status_code == 200
    assert dev_client.get("/redoc").status_code == 200
    assert dev_client.get("/openapi.json").status_code == 200


def test_17_production_paypal_callback_fails_closed_without_localhost(monkeypatch):
    """17. Production PayPal callbacks fail closed when HTTPS FRONTEND_URL/callbacks are absent."""
    monkeypatch.setenv("RESTOCKAI_ENV", "production")
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    monkeypatch.delenv("PAYPAL_RETURN_URL", raising=False)
    monkeypatch.delenv("PAYPAL_CANCEL_URL", raising=False)

    with pytest.raises(ValueError, match="localhost fallback is disabled"):
        _resolve_frontend_callback_url("PAYPAL_RETURN_URL", "/checkout/success")

    monkeypatch.setenv("FRONTEND_URL", "http://localhost:5173")
    with pytest.raises(ValueError, match="non-localhost https://"):
        _resolve_frontend_callback_url("PAYPAL_CANCEL_URL", "/checkout/cancel")

    monkeypatch.setenv("FRONTEND_URL", PROD_FRONTEND_URL)
    assert (
        _resolve_frontend_callback_url("PAYPAL_RETURN_URL", "/checkout/success")
        == f"{PROD_FRONTEND_URL}/checkout/success"
    )
