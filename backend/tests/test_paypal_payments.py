import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.auth.service import reset_auth_runtime_state
from app.database import SessionLocal
from app.models.commerce import RecoveryOrder, RecoveryOrderStatus, RecoveryFulfillmentStatus
from app.payments.models import PaymentTransaction, PaymentStatus

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_mode(monkeypatch):
    """Ensure tests run deterministically with mock sandbox client and valid demo auth session."""
    from app.payments.config import paypal_settings
    monkeypatch.setattr(paypal_settings, "client_id", "")
    monkeypatch.setattr(paypal_settings, "client_secret", "")
    monkeypatch.setattr(paypal_settings, "allow_mock", True)
    monkeypatch.setenv("RESTOCKAI_DEMO_PASSWORD", "test-suite-pass")
    monkeypatch.setenv("RESTOCKAI_SESSION_SECRET", "test-suite-secret-0123456789abcdef")
    reset_auth_runtime_state()
    res = client.post("/api/auth/login", json={"password": "test-suite-pass"})
    assert res.status_code == 200
    client.headers.update({"X-CSRF-Token": res.json()["csrf_token"]})

@pytest.fixture
def test_order():
    """Creates a temporary recovery order in the database for payment testing."""
    order_id = f"TEST-ORD-{uuid.uuid4().hex[:6].upper()}"
    with SessionLocal() as db:
        order = RecoveryOrder(
            order_id=order_id,
            sku_id="YOG-001",
            product_name="Greek Yogurt 500g",
            source_store_id="STORE_A",
            channel="DISCOUNT_MARKETPLACE",
            quantity=10,
            unit_price=2.50,
            total_amount=25.00,
            currency="USD",
            buyer_name="Test Buyer",
            buyer_email="buyer@test.com",
            status=RecoveryOrderStatus.CREATED.value,
            fulfillment_status=RecoveryFulfillmentStatus.UNFULFILLED.value,
        )
        db.add(order)
        db.commit()

    yield order_id

    # Cleanup
    with SessionLocal() as db:
        db.query(PaymentTransaction).filter(PaymentTransaction.recovery_order_id == order_id).delete()
        db.query(RecoveryOrder).filter(RecoveryOrder.order_id == order_id).delete()
        db.commit()


def test_paypal_config_endpoint():
    """Verify PayPal configuration endpoint returns client_id and mode without exposing secret."""
    res = client.get("/api/payments/config")
    assert res.status_code == 200
    data = res.json()
    assert "client_id" in data
    assert "currency" in data
    assert "mode" in data
    assert "client_secret" not in data


def test_create_paypal_order_success(test_order):
    """Verify creating a PayPal order calculates total strictly from DB record."""
    res = client.post(
        "/api/payments/paypal/create-order",
        json={"recovery_order_id": test_order},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["recovery_order_id"] == test_order
    assert data["amount"] == 25.00
    assert data["currency"] == "USD"
    assert "paypal_order_id" in data
    assert data["paypal_order_id"].startswith("PAYPAL-ORD-")
    assert data["approval_url"] is not None

    # Verify status in database transitioned to PENDING_PAYMENT
    with SessionLocal() as db:
        ord_db = db.query(RecoveryOrder).filter(RecoveryOrder.order_id == test_order).first()
        assert ord_db.status == RecoveryOrderStatus.PENDING_PAYMENT.value
        assert ord_db.payment_id == data["payment_id"]


def test_create_paypal_order_idempotency(test_order):
    """Verify duplicate create-order requests with same idempotency key return existing order."""
    idem_key = f"idem-{uuid.uuid4().hex}"
    
    res1 = client.post(
        "/api/payments/paypal/create-order",
        json={"recovery_order_id": test_order, "idempotency_key": idem_key},
    )
    assert res1.status_code == 200
    order_id_1 = res1.json()["paypal_order_id"]

    res2 = client.post(
        "/api/payments/paypal/create-order",
        json={"recovery_order_id": test_order, "idempotency_key": idem_key},
    )
    assert res2.status_code == 200
    order_id_2 = res2.json()["paypal_order_id"]

    assert order_id_1 == order_id_2


def test_capture_paypal_order_success(test_order):
    """Verify capturing buyer-approved payment validates amount and marks order PAID."""
    # 1. Create order
    create_res = client.post(
        "/api/payments/paypal/create-order",
        json={"recovery_order_id": test_order},
    )
    paypal_order_id = create_res.json()["paypal_order_id"]

    # 2. Capture payment
    capture_res = client.post(
        "/api/payments/paypal/capture",
        json={"paypal_order_id": paypal_order_id, "recovery_order_id": test_order},
    )
    assert capture_res.status_code == 200
    capture_data = capture_res.json()
    assert capture_data["status"] == "CAPTURED"
    assert capture_data["paypal_capture_id"].startswith("CAP-")
    assert capture_data["amount"] == 25.00
    assert capture_data["currency"] == "USD"
    assert capture_data["payer_email"] == "sandbox-buyer@restockai.io"

    # 3. Verify Database state: Order must be PAID, Fulfillment remains UNFULFILLED
    with SessionLocal() as db:
        ord_db = db.query(RecoveryOrder).filter(RecoveryOrder.order_id == test_order).first()
        assert ord_db.status == RecoveryOrderStatus.PAID.value
        assert ord_db.fulfillment_status == RecoveryFulfillmentStatus.UNFULFILLED.value
        assert ord_db.paid_at is not None

        txn_db = db.query(PaymentTransaction).filter(PaymentTransaction.paypal_order_id == paypal_order_id).first()
        assert txn_db.status == PaymentStatus.CAPTURED.value
        assert txn_db.paypal_capture_id == capture_data["paypal_capture_id"]


def test_duplicate_capture_prevention(test_order):
    """Verify duplicate capture requests are safely handled and return existing capture."""
    create_res = client.post(
        "/api/payments/paypal/create-order",
        json={"recovery_order_id": test_order},
    )
    paypal_order_id = create_res.json()["paypal_order_id"]

    # First capture
    res1 = client.post("/api/payments/paypal/capture", json={"paypal_order_id": paypal_order_id})
    assert res1.status_code == 200
    cap_id_1 = res1.json()["paypal_capture_id"]

    # Second capture (duplicate)
    res2 = client.post("/api/payments/paypal/capture", json={"paypal_order_id": paypal_order_id})
    assert res2.status_code == 200
    cap_id_2 = res2.json()["paypal_capture_id"]

    assert cap_id_1 == cap_id_2


def test_create_order_fails_for_already_paid(test_order):
    """Verify already paid orders cannot be paid again."""
    create_res = client.post("/api/payments/paypal/create-order", json={"recovery_order_id": test_order})
    paypal_order_id = create_res.json()["paypal_order_id"]
    client.post("/api/payments/paypal/capture", json={"paypal_order_id": paypal_order_id})

    # Try creating another payment order for the same paid recovery order
    dup_res = client.post("/api/payments/paypal/create-order", json={"recovery_order_id": test_order})
    assert dup_res.status_code == 400
    assert "already paid" in dup_res.json()["detail"].lower()


def test_buyer_cancellation_handling(test_order):
    """Verify buyer cancellation marks transaction CANCELLED."""
    create_res = client.post("/api/payments/paypal/create-order", json={"recovery_order_id": test_order})
    paypal_order_id = create_res.json()["paypal_order_id"]

    cancel_res = client.post(
        "/api/payments/paypal/cancel",
        json={"paypal_order_id": paypal_order_id, "reason": "Buyer closed PayPal popup"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    with SessionLocal() as db:
        txn = db.query(PaymentTransaction).filter(PaymentTransaction.paypal_order_id == paypal_order_id).first()
        assert txn.status == PaymentStatus.CANCELLED.value


def test_payment_status_retrieval(test_order):
    """Verify GET /api/payments/{payment_id} and GET /api/payments/order/{recovery_order_id}."""
    create_res = client.post("/api/payments/paypal/create-order", json={"recovery_order_id": test_order})
    payment_id = create_res.json()["payment_id"]

    # 1. By Payment ID
    res1 = client.get(f"/api/payments/{payment_id}")
    assert res1.status_code == 200
    assert res1.json()["payment_id"] == payment_id
    assert res1.json()["amount"] == 25.00

    # 2. By Recovery Order ID
    res2 = client.get(f"/api/payments/order/{test_order}")
    assert res2.status_code == 200
    items = res2.json()
    assert len(items) >= 1
    assert items[0]["payment_id"] == payment_id


@pytest.mark.asyncio
async def test_agent_workforce_commerce_and_finance_reconciliation():
    """
    Verify workforce agents integration:
    1. Commerce Agent (5) structures an eligible recovery order.
    2. PayPal creates and captures buyer-approved payment.
    3. Finance Agent (7) reconciles verified PayPal capture and computes margin variance.
    """
    from app.agent.workforce import execute_commerce_agent, execute_finance_agent

    # Step 1: Commerce Agent prepares order
    com_result = await execute_commerce_agent(
        sku_id="YOG-001",
        source_store_id="STORE_A",
        quantity=20,
        unit_price=2.00,
        action_type="DISCOUNT",
        channel="DISCOUNT_MARKETPLACE",
    )
    assert com_result.agent_id == 5
    assert com_result.order_id is not None
    assert com_result.total_amount == 40.00
    assert com_result.payment_status == "PENDING_PAYMENT"

    # Step 2: PayPal Payment Flow
    create_res = client.post("/api/payments/paypal/create-order", json={"recovery_order_id": com_result.order_id})
    assert create_res.status_code == 200
    paypal_order_id = create_res.json()["paypal_order_id"]
    payment_id = create_res.json()["payment_id"]

    capture_res = client.post("/api/payments/paypal/capture", json={"paypal_order_id": paypal_order_id})
    assert capture_res.status_code == 200
    assert capture_res.json()["status"] == "CAPTURED"

    # Step 3: Finance Agent reconciles verified transaction
    fin_result = await execute_finance_agent(
        payment_id=payment_id,
        recovery_order_id=com_result.order_id,
        predicted_net_recovery=40.00,
    )
    assert fin_result.agent_id == 7
    assert fin_result.reconciliation_status == "RECONCILED"
    assert fin_result.captured_amount == 40.00
    assert fin_result.fee_deducted is not None
    assert "Verified PayPal Capture" in fin_result.audit_notes

    # Cleanup
    with SessionLocal() as db:
        db.query(PaymentTransaction).filter(PaymentTransaction.recovery_order_id == com_result.order_id).delete()
        db.query(RecoveryOrder).filter(RecoveryOrder.order_id == com_result.order_id).delete()
        db.commit()


def test_upstream_paypal_401_mapped_to_502_not_session_logout(test_order):
    """Upstream PayPal OAuth 401 failures must return 502 so the frontend session stays logged in."""
    from unittest.mock import patch
    from app.payments.paypal_client import PayPalClientError

    with patch(
        "app.payments.service.paypal_client.create_order",
        side_effect=PayPalClientError("PayPal OAuth authentication failed", status_code=401),
    ):
        res = client.post("/api/payments/paypal/create-order", json={"recovery_order_id": test_order})
        assert res.status_code == 502
        assert "PayPal API error" in res.json()["detail"]

    # Authenticated session cookie remains valid
    assert client.get("/api/auth/session").status_code == 200

