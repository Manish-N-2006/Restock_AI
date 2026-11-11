import pytest
from unittest.mock import MagicMock, patch
from backend.app.payments.service import payment_service
from backend.app.payments.schemas import CreatePayPalOrderRequest, CapturePayPalOrderRequest

def test_simulation_order_creation_and_capture():
    """Verify simulation orders (SIM-ORD-*) are seamlessly handled by PaymentService without 404s."""
    db_mock = MagicMock()
    # Explicitly return None so it triggers the simulation order lookup
    db_mock.query.return_value.filter.return_value.first.return_value = None

    mock_paypal_order = {
        "id": "PAYPAL-ORD-TEST12345",
        "status": "CREATED",
        "links": [
            {"href": "https://www.sandbox.paypal.com/checkoutnow?token=PAYPAL-ORD-TEST12345", "rel": "approve"}
        ]
    }
    mock_paypal_capture = {
        "id": "PAYPAL-ORD-TEST12345",
        "status": "COMPLETED",
        "purchase_units": [{
            "payments": {
                "captures": [{
                    "id": "CAP-SIM-998877",
                    "status": "COMPLETED",
                    "amount": {"value": "187.20", "currency_code": "USD"},
                    "seller_receivable_breakdown": {
                        "paypal_fee": {"value": "6.77"},
                        "net_amount": {"value": "180.43"}
                    }
                }]
            }
        }],
        "payer": {
            "payer_id": "TEST_PAYER_01",
            "email_address": "buyer@metroretail.example.com",
            "name": {"given_name": "Metro", "surname": "Buyer"}
        }
    }

    with patch("backend.app.payments.service.paypal_client.create_order", return_value=mock_paypal_order), \
         patch("backend.app.payments.service.paypal_client.capture_order", return_value=mock_paypal_capture):

        # 1. Create order for simulation order ID
        sim_order_id = "SIM-ORD-6E6C08"
        req = CreatePayPalOrderRequest(
            recovery_order_id=sim_order_id,
            idempotency_key=f"test-idem-{sim_order_id}",
        )
        res = payment_service.create_paypal_order(db=db_mock, request=req)

        assert res.recovery_order_id == sim_order_id
        assert res.paypal_order_id == "PAYPAL-ORD-TEST12345"
        assert res.amount == 187.20
        assert res.currency == "USD"
        assert res.status == "PENDING_APPROVAL"
        assert res.approval_url == "https://www.sandbox.paypal.com/checkoutnow?token=PAYPAL-ORD-TEST12345"

        # 2. Verify duplicate create order hits idempotency cache
        res_idem = payment_service.create_paypal_order(db=db_mock, request=req)
        assert res_idem.paypal_order_id == res.paypal_order_id

        # 3. Capture simulation order
        cap_req = CapturePayPalOrderRequest(
            paypal_order_id=res.paypal_order_id,
            recovery_order_id=sim_order_id,
        )
        cap_res = payment_service.capture_paypal_order(db=db_mock, request=cap_req)

        assert cap_res.recovery_order_id == sim_order_id
        assert cap_res.paypal_order_id == "PAYPAL-ORD-TEST12345"
        assert cap_res.paypal_capture_id == "CAP-SIM-998877"
        assert cap_res.capture_id == "CAP-SIM-998877"
        assert cap_res.payment_id == res.payment_id
        assert cap_res.status == "CAPTURED"
        assert cap_res.capture_status == "COMPLETED"
        assert cap_res.payment_status == "CAPTURED"
        assert cap_res.reconciliation_status == "PENDING"
        assert cap_res.amount == 187.20
        assert cap_res.fee_amount == 6.77
        assert cap_res.net_amount == 180.43
        assert cap_res.buyer_details is not None
        assert cap_res.buyer_details["payer_id"] == "TEST_PAYER_01"

        # 4. Verify simulation payment can be inspected by payment_id
        inspected = payment_service.get_simulation_payment(res.payment_id)
        assert inspected is not None
        assert inspected["payment_id"] == res.payment_id
        assert inspected["paypal_capture_id"] == "CAP-SIM-998877"
        assert inspected["capture_id"] == "CAP-SIM-998877"
        assert inspected["paypal_order_id"] == "PAYPAL-ORD-TEST12345"
        assert inspected["amount"] == 187.20
        assert inspected["currency"] == "USD"
        assert inspected["status"] == "CAPTURED"
        assert inspected["capture_status"] == "COMPLETED"
        assert inspected["buyer_details"]["payer_name"] == "Metro Buyer"

        # 5. Verify duplicate capture is idempotent
        cap_duplicate = payment_service.capture_paypal_order(db=db_mock, request=cap_req)
        assert cap_duplicate.payment_id == res.payment_id
        assert cap_duplicate.paypal_capture_id == "CAP-SIM-998877"
        assert cap_duplicate.status == "CAPTURED"
        assert cap_duplicate.capture_status == "COMPLETED"


def test_simulation_capture_validation_failures():
    """Verify payment validation rejects non-COMPLETED status and amount tampering."""
    from fastapi import HTTPException

    db_mock = MagicMock()
    db_mock.query.return_value.filter.return_value.first.return_value = None

    # Pre-populate simulation transaction expecting 187.20
    test_order_id = "PAYPAL-ORD-FAILTEST"
    payment_service._simulation_transactions[test_order_id] = {
        "payment_id": "PAY-FAIL-01",
        "recovery_order_id": "SIM-ORD-FAIL",
        "paypal_order_id": test_order_id,
        "amount": 187.20,
        "currency": "USD",
        "status": "PENDING_APPROVAL",
    }

    # Case A: PayPal status is FAILED/DECLINED
    mock_failed_capture = {
        "id": test_order_id,
        "status": "FAILED",
        "purchase_units": [],
    }
    with patch("backend.app.payments.service.paypal_client.capture_order", return_value=mock_failed_capture):
        with pytest.raises(HTTPException) as exc_info:
            payment_service.capture_paypal_order(
                db=db_mock,
                request=CapturePayPalOrderRequest(paypal_order_id=test_order_id, recovery_order_id="SIM-ORD-FAIL")
            )
        assert exc_info.value.status_code == 400

    # Case B: Amount mismatch tampering (Captured 50.00 vs expected 187.20)
    mock_tampered_capture = {
        "id": test_order_id,
        "status": "COMPLETED",
        "purchase_units": [{
            "payments": {
                "captures": [{
                    "id": "CAP-TAMPERED-01",
                    "status": "COMPLETED",
                    "amount": {"value": "50.00", "currency_code": "USD"},
                    "seller_receivable_breakdown": {
                        "paypal_fee": {"value": "1.50"},
                        "net_amount": {"value": "48.50"}
                    }
                }]
            }
        }],
    }
    with patch("backend.app.payments.service.paypal_client.capture_order", return_value=mock_tampered_capture):
        with pytest.raises(HTTPException) as exc_info:
            payment_service.capture_paypal_order(
                db=db_mock,
                request=CapturePayPalOrderRequest(paypal_order_id=test_order_id, recovery_order_id="SIM-ORD-FAIL")
            )
        assert exc_info.value.status_code == 400
        assert "Amount mismatch" in exc_info.value.detail


def test_scenario_d_fulfillment_blocked_until_payment_captured():
    """Verify Stage 8 fulfillment halts if PayPal payment is not in CAPTURED status for Scenario D."""
    import asyncio
    from backend.app.services.simulation_orchestrator import simulation_orchestrator

    async def _run():
        print("\n--- STEP A: reset_simulation ---")
        state = await simulation_orchestrator.reset_simulation("SCENARIO_D")
        run_id = state.simulation_run_id
        print("--- STEP B: loop 1..5 ---")
        while state.current_step_index < 5:
            print(f"    calling execute_step from idx={state.current_step_index}")
            state = await simulation_orchestrator.execute_step(run_id)
            print(f"    stepped to idx={state.current_step_index}")

        print("--- STEP C: execute stage 6 ---")
        state = await simulation_orchestrator.execute_step(run_id)
        print(f"--- STEP D: stage 6 done, status={state.status} ---")
        state = await simulation_orchestrator.approve_pending_decision(run_id, "APPROVED")
        print(f"--- STEP E: approved, status={state.status}, idx={state.current_step_index} ---")

        state.current_step_index = 7
        blocked_state = await simulation_orchestrator.execute_step(run_id)
        print(f"--- STEP F: blocked_state status={blocked_state.status} ---")
        assert blocked_state.status == "AWAITING_PAYMENT"

    asyncio.run(_run())


def test_scenario_d_payment_events_and_reconciliation():
    """Verify Scenario D records PAYMENT_APPROVAL_RECEIVED, PAYMENT_CAPTURE_STARTED, PAYMENT_CAPTURED, and PAYMENT_RECONCILED with payment_id."""
    import asyncio
    from backend.app.services.simulation_orchestrator import simulation_orchestrator

    async def _run():
        with patch("backend.app.services.routing_service.routing_service.query_road_network", return_value=None):
            state = await simulation_orchestrator.reset_simulation("SCENARIO_D")
            run_id = state.simulation_run_id

            # Advance through Stages 1 to 5
            while state.current_step_index < 5:
                state = await simulation_orchestrator.execute_step(run_id)

            # Stage 6: Human Approval
            state = await simulation_orchestrator.execute_step(run_id)
            assert state.status == "AWAITING_APPROVAL"
            state = await simulation_orchestrator.approve_pending_decision(run_id, "APPROVED")

            assert state.status == "AWAITING_PAYMENT"

            # Confirm verified capture
            test_payment_id = "PAY-SIM-VERIFIED-001"
            test_paypal_order = "PAYPAL-ORD-VERIFY-001"
            test_capture_id = "CAP-SIM-VERIFY-001"

            confirmed_state = await simulation_orchestrator.confirm_paypal_capture(
                run_id=run_id,
                paypal_order_id=test_paypal_order,
                paypal_capture_id=test_capture_id,
                amount=216.00,
                currency="USD",
                payment_id=test_payment_id,
                fee_amount=8.03,
                net_amount=207.97,
                payer_id="PAYER-BUYER-01",
                payer_email="buyer@metro.example.com",
                payer_name="Metro Retail Buyer",
            )

            # 1. Verification of PayPal Checkout state
            checkout = confirmed_state.paypal_checkout
            assert checkout["status"] == "CAPTURED"
            assert checkout["payment_id"] == test_payment_id
            assert checkout["paypal_order_id"] == test_paypal_order
            assert checkout["paypal_capture_id"] == test_capture_id
            assert checkout["capture_id"] == test_capture_id
            assert checkout["amount"] == 216.00
            assert checkout["fee_amount"] == 8.03
            assert checkout["net_amount"] == 207.97
            assert checkout["buyer_details"]["payer_name"] == "Metro Retail Buyer"

            # 2. Verification of live feed events
            actions = [e["action"] for e in confirmed_state.live_event_feed]
            assert "PAYMENT_APPROVAL_RECEIVED" in actions
            assert "PAYMENT_CAPTURE_STARTED" in actions
            assert "PAYMENT_CAPTURED" in actions

            captured_event = next(e for e in confirmed_state.live_event_feed if e["action"] == "PAYMENT_CAPTURED")
            assert test_payment_id in captured_event["details"]
            assert test_capture_id in captured_event["details"]

            # 3. Complete Stage 9 (Reconciliation)
            final_state = await simulation_orchestrator.execute_step(run_id)
            assert final_state.status == "COMPLETED"

            reconciled_events = [e for e in final_state.live_event_feed if e["action"] == "PAYMENT_RECONCILED"]
            assert len(reconciled_events) >= 1
            assert test_payment_id in reconciled_events[0]["details"]
            assert final_state.paypal_checkout["reconciliation_status"] == "RECONCILED"
            assert final_state.financial_reconciliation["status"] == "RECONCILED"
            assert final_state.financial_reconciliation["net_recovery"] == 207.97

    asyncio.run(_run())


def test_scenario_d_duplicate_confirm_idempotency():
    """Verify calling confirm_paypal_capture twice with the same capture_id is idempotent and doesn't duplicate events."""
    import asyncio
    from backend.app.services.simulation_orchestrator import simulation_orchestrator

    async def _run():
        with patch("backend.app.services.routing_service.routing_service.query_road_network", return_value=None):
            state = await simulation_orchestrator.reset_simulation("SCENARIO_D")
            run_id = state.simulation_run_id

            while state.current_step_index < 5:
                state = await simulation_orchestrator.execute_step(run_id)

            # Stage 6: Human Approval
            state = await simulation_orchestrator.execute_step(run_id)
            assert state.status == "AWAITING_APPROVAL"
            state = await simulation_orchestrator.approve_pending_decision(run_id, "APPROVED")

            # Stage 7: Checkout (already at AWAITING_PAYMENT)
            assert state.status == "AWAITING_PAYMENT"

            # First confirmation
            state1 = await simulation_orchestrator.confirm_paypal_capture(
                run_id=run_id,
                paypal_order_id="ORD-IDEMPOTENT-01",
                paypal_capture_id="CAP-IDEMPOTENT-01",
                amount=216.00,
                currency="USD",
                payment_id="PAY-IDEMPOTENT-01",
            )
            captured_count_1 = sum(1 for e in state1.live_event_feed if e["action"] == "PAYMENT_CAPTURED")
            assert captured_count_1 == 1

            # Second confirmation with same capture ID
            state2 = await simulation_orchestrator.confirm_paypal_capture(
                run_id=run_id,
                paypal_order_id="ORD-IDEMPOTENT-01",
                paypal_capture_id="CAP-IDEMPOTENT-01",
                amount=216.00,
                currency="USD",
                payment_id="PAY-IDEMPOTENT-01",
            )
            captured_count_2 = sum(1 for e in state2.live_event_feed if e["action"] == "PAYMENT_CAPTURED")
            assert captured_count_2 == 1  # No duplicate event added
            assert state2.paypal_checkout["payment_id"] == "PAY-IDEMPOTENT-01"

    asyncio.run(_run())


def test_scenarios_a_b_c_bypass_paypal():
    """Verify Scenarios A, B, and C mark settlement as NOT_APPLICABLE and bypass PayPal without requiring external capture."""
    import asyncio
    from backend.app.services.simulation_orchestrator import simulation_orchestrator

    async def _run():
        with patch("backend.app.services.routing_service.routing_service.query_road_network", return_value=None):
            for scn in ["SCENARIO_A", "SCENARIO_B", "SCENARIO_C"]:
                state = await simulation_orchestrator.reset_simulation(scn)
                # Advance through all steps to completion
                for _ in range(9):
                    if state.status == "AWAITING_APPROVAL":
                        state = await simulation_orchestrator.approve_pending_decision(state.simulation_run_id, "APPROVED")
                    else:
                        state = await simulation_orchestrator.execute_step(state.simulation_run_id)
                    if state.status == "COMPLETED":
                        break

                assert state.status == "COMPLETED"
                assert state.paypal_checkout["status"] == "NOT_APPLICABLE"
                assert "Internal multi-branch inventory redistribution" in state.paypal_checkout["details"]
                # Ensure no payment required events were triggered
                actions = [e["action"] for e in state.live_event_feed]
                assert "CHECKOUT_READY" not in actions

    asyncio.run(_run())
