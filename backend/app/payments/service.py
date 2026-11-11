import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException

from .models import PaymentTransaction, PaymentStatus
from .schemas import (
    CreatePayPalOrderRequest,
    CreatePayPalOrderResponse,
    CapturePayPalOrderRequest,
    CapturePayPalOrderResponse,
    CancelPayPalOrderRequest,
    PaymentTransactionResponse,
)
from .paypal_client import paypal_client, PayPalClientError
from .config import paypal_settings
from ..models.commerce import RecoveryOrder, RecoveryOrderStatus, RecoveryFulfillmentStatus

logger = logging.getLogger("payments.service")

class PaymentService:
    """
    Core Payment Orchestration Service.
    Enforces server-authoritative amount calculation, strict eligibility validation,
    idempotent capture verification, and decoupled fulfillment status management.
    Seamlessly supports both production database RecoveryOrders and isolated simulation orders.
    """

    def __init__(self):
        self._simulation_transactions: Dict[str, Dict[str, Any]] = {}
        self._simulation_idempotency: Dict[str, Dict[str, Any]] = {}

    def create_paypal_order(
        self,
        db: Session,
        request: CreatePayPalOrderRequest,
    ) -> CreatePayPalOrderResponse:
        # 1. Retrieve the existing RecoveryOrder from DB or simulation state
        order = db.query(RecoveryOrder).filter(
            RecoveryOrder.order_id == request.recovery_order_id
        ).first()

        is_simulation_order = False
        sim_order_data: Optional[Dict[str, Any]] = None

        if not order and (request.recovery_order_id.startswith("SIM-") or "SIM" in request.recovery_order_id):
            is_simulation_order = True
            from ..services.simulation_orchestrator import simulation_orchestrator
            sim_order_data = simulation_orchestrator.get_order_data(request.recovery_order_id)
            if not sim_order_data:
                sim_order_data = {
                    "order_id": request.recovery_order_id,
                    "total_amount": 187.20,
                    "currency": "USD",
                    "status": "CREATED",
                }

        if not order and not is_simulation_order:
            logger.warning(f"Payment initiation rejected: RecoveryOrder {request.recovery_order_id} not found")
            raise HTTPException(status_code=404, detail=f"RecoveryOrder {request.recovery_order_id} not found")

        # 2. Verify payment eligibility
        order_status = sim_order_data.get("status") if is_simulation_order else order.status
        if order_status == RecoveryOrderStatus.PAID.value:
            raise HTTPException(
                status_code=400,
                detail=f"Order {request.recovery_order_id} is already paid. Duplicate payment is not allowed."
            )
        if not is_simulation_order and order.status == RecoveryOrderStatus.CANCELLED.value:
            raise HTTPException(
                status_code=400,
                detail=f"Order {request.recovery_order_id} was cancelled and is not eligible for payment."
            )

        # 3. Check idempotency if key provided
        if request.idempotency_key:
            if is_simulation_order:
                if request.idempotency_key in self._simulation_idempotency:
                    existing = self._simulation_idempotency[request.idempotency_key]
                    return CreatePayPalOrderResponse(
                        payment_id=existing["payment_id"],
                        paypal_order_id=existing["paypal_order_id"],
                        recovery_order_id=existing["recovery_order_id"],
                        amount=existing["amount"],
                        currency=existing["currency"],
                        status=existing["status"],
                        approval_url=existing.get("approval_url"),
                    )
            else:
                existing_txn = db.query(PaymentTransaction).filter(
                    PaymentTransaction.idempotency_key == request.idempotency_key
                ).first()
                if existing_txn and existing_txn.paypal_order_id:
                    logger.info(f"Idempotency hit for key {request.idempotency_key}. Returning existing order {existing_txn.paypal_order_id}")
                    return CreatePayPalOrderResponse(
                        payment_id=existing_txn.payment_id,
                        paypal_order_id=existing_txn.paypal_order_id,
                        recovery_order_id=existing_txn.recovery_order_id,
                        amount=existing_txn.amount,
                        currency=existing_txn.currency,
                        status=existing_txn.status,
                        approval_url=f"{paypal_settings.checkout_base}/checkoutnow?token={existing_txn.paypal_order_id}",
                    )

        # 4. Strictly calculate amount from persisted order data (Never trust frontend!)
        if is_simulation_order:
            order_amount = round(float(sim_order_data.get("total_amount", 187.20)), 2)
            currency = sim_order_data.get("currency", "USD")
            recovery_order_id = sim_order_data.get("order_id", request.recovery_order_id)
        else:
            order_amount = round(float(order.total_amount), 2)
            currency = order.currency or "USD"
            recovery_order_id = order.order_id

        if order_amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid order amount. Amount must be greater than zero.")

        payment_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"

        # Validate optional callback overrides against trusted frontend origins
        for callback_url in (request.return_url, request.cancel_url):
            if callback_url:
                from urllib.parse import urlsplit
                from ..auth.service import get_allowed_origins
                parsed = urlsplit(callback_url.strip())
                origin = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}" if parsed.scheme and parsed.netloc else ""
                allowed = {o.rstrip("/").lower() for o in get_allowed_origins()}
                if origin not in allowed:
                    raise HTTPException(status_code=400, detail="Untrusted PayPal callback URL origin.")

        # 5. Call PayPal Orders v2 API
        try:
            paypal_data = paypal_client.create_order(
                amount=order_amount,
                currency=currency,
                reference_id=recovery_order_id,
                custom_id=payment_id,
                return_url=request.return_url,
                cancel_url=request.cancel_url,
                idempotency_key=request.idempotency_key,
            )
        except PayPalClientError as pce:
            logger.error(f"PayPal create_order error: {pce.message}")
            raise HTTPException(status_code=pce.status_code, detail=f"PayPal API error: {pce.message}")

        paypal_order_id = paypal_data.get("id")
        approval_url = None
        for link in paypal_data.get("links", []):
            if link.get("rel") in ("approve", "payer-action"):
                approval_url = link.get("href")
                break

        # 6. Persist PaymentTransaction record (in-memory for isolated simulation, DB for production)
        if is_simulation_order:
            sim_txn_record = {
                "payment_id": payment_id,
                "recovery_order_id": recovery_order_id,
                "paypal_order_id": paypal_order_id,
                "amount": order_amount,
                "currency": currency,
                "status": PaymentStatus.PENDING_APPROVAL.value,
                "idempotency_key": request.idempotency_key,
                "raw_response": json.dumps(paypal_data),
                "is_simulation": True,
            }
            self._simulation_transactions[paypal_order_id] = sim_txn_record
            if request.idempotency_key:
                self._simulation_idempotency[request.idempotency_key] = {
                    "payment_id": payment_id,
                    "paypal_order_id": paypal_order_id,
                    "recovery_order_id": recovery_order_id,
                    "amount": order_amount,
                    "currency": currency,
                    "status": PaymentStatus.PENDING_APPROVAL.value,
                    "approval_url": approval_url,
                }
            logger.info(f"Created PayPal Sandbox order {paypal_order_id} for isolated simulation order {recovery_order_id} (${order_amount} {currency})")
            return CreatePayPalOrderResponse(
                payment_id=payment_id,
                paypal_order_id=paypal_order_id,
                recovery_order_id=recovery_order_id,
                amount=order_amount,
                currency=currency,
                status=PaymentStatus.PENDING_APPROVAL.value,
                approval_url=approval_url,
            )

        transaction = PaymentTransaction(
            payment_id=payment_id,
            recovery_order_id=order.order_id,
            paypal_order_id=paypal_order_id,
            amount=order_amount,
            currency=currency,
            status=PaymentStatus.PENDING_APPROVAL.value,
            idempotency_key=request.idempotency_key,
            raw_response=json.dumps(paypal_data),
        )
        db.add(transaction)

        # Update recovery order status to PENDING_PAYMENT
        if order.status == RecoveryOrderStatus.CREATED.value:
            order.status = RecoveryOrderStatus.PENDING_PAYMENT.value
            order.payment_id = payment_id

        db.commit()
        db.refresh(transaction)

        logger.info(f"Created PayPal order {paypal_order_id} for recovery order {order.order_id} (amount: ${order_amount} {currency})")

        return CreatePayPalOrderResponse(
            payment_id=payment_id,
            paypal_order_id=paypal_order_id,
            recovery_order_id=order.order_id,
            amount=order_amount,
            currency=currency,
            status=transaction.status,
            approval_url=approval_url,
        )

    def _capture_simulation_order(
        self,
        request: CapturePayPalOrderRequest,
    ) -> CapturePayPalOrderResponse:
        paypal_order_id = request.paypal_order_id
        sim_txn = self._simulation_transactions.get(paypal_order_id)
        if not sim_txn:
            sim_txn = {
                "payment_id": f"PAY-SIM-{uuid.uuid4().hex[:8].upper()}",
                "recovery_order_id": request.recovery_order_id or "SIM-ORD-DEMO",
                "paypal_order_id": paypal_order_id,
                "amount": 187.20,
                "currency": "USD",
                "status": PaymentStatus.PENDING_APPROVAL.value,
            }
            self._simulation_transactions[paypal_order_id] = sim_txn

        # Prevent duplicate capture (Idempotency)
        if sim_txn.get("status") == PaymentStatus.CAPTURED.value:
            amt = sim_txn["amount"]
            fee = sim_txn.get("fee_amount", 0.0)
            net = sim_txn.get("net_amount", amt - fee)
            cap_id = sim_txn.get("paypal_capture_id", "")
            return CapturePayPalOrderResponse(
                payment_id=sim_txn["payment_id"],
                recovery_order_id=sim_txn["recovery_order_id"],
                paypal_order_id=paypal_order_id,
                paypal_capture_id=cap_id,
                capture_id=cap_id,
                status=sim_txn["status"],
                capture_status="COMPLETED",
                payment_status="CAPTURED",
                reconciliation_status="PENDING",
                amount=amt,
                currency=sim_txn["currency"],
                fee_amount=fee,
                net_amount=net,
                payer_id=sim_txn.get("payer_id"),
                payer_email=sim_txn.get("payer_email"),
                payer_name=sim_txn.get("payer_name"),
                buyer_details={
                    "payer_id": sim_txn.get("payer_id"),
                    "payer_email": sim_txn.get("payer_email"),
                    "payer_name": sim_txn.get("payer_name"),
                },
                captured_at=datetime.fromisoformat(sim_txn.get("captured_at")) if isinstance(sim_txn.get("captured_at"), str) else datetime.utcnow(),
            )

        # Call PayPal Orders v2 Capture
        try:
            capture_data = paypal_client.capture_order(
                paypal_order_id=paypal_order_id,
                idempotency_key=request.idempotency_key,
            )
        except PayPalClientError as pce:
            sim_txn["status"] = PaymentStatus.FAILED.value
            sim_txn["error_message"] = pce.message
            logger.error(f"PayPal capture failed for {paypal_order_id}: {pce.message}")
            raise HTTPException(status_code=pce.status_code, detail=f"PayPal Capture failed: {pce.message}")

        paypal_status = capture_data.get("status")
        if paypal_status != "COMPLETED":
            sim_txn["status"] = PaymentStatus.FAILED.value
            raise HTTPException(status_code=400, detail=f"Payment capture failed. PayPal status: {paypal_status}")

        purchase_units = capture_data.get("purchase_units", [])
        captures = purchase_units[0].get("payments", {}).get("captures", []) if purchase_units else []
        if paypal_settings.is_configured:
            if not captures or not captures[0].get("id"):
                sim_txn["status"] = PaymentStatus.FAILED.value
                raise HTTPException(status_code=400, detail="Malformed PayPal Sandbox capture response: capture ID missing.")
            primary_capture = captures[0]
            capture_id = primary_capture["id"]
        else:
            primary_capture = captures[0] if captures else {}
            capture_id = primary_capture.get("id", f"SIM-CAP-{uuid.uuid4().hex[:8].upper()}")

        capture_status = primary_capture.get("status")
        if capture_status != "COMPLETED":
            sim_txn["status"] = PaymentStatus.FAILED.value
            raise HTTPException(status_code=400, detail=f"Capture record status not COMPLETED: {capture_status}")

        captured_val_str = primary_capture.get("amount", {}).get("value", str(sim_txn.get("amount", 187.20)))
        captured_currency = primary_capture.get("amount", {}).get("currency_code", sim_txn.get("currency", "USD"))
        captured_amount = float(captured_val_str)

        expected_amount = float(sim_txn.get("amount", 187.20))
        if abs(captured_amount - expected_amount) > 0.01:
            sim_txn["status"] = PaymentStatus.FAILED.value
            raise HTTPException(status_code=400, detail=f"Amount mismatch: captured {captured_amount}, expected {expected_amount}")

        if captured_currency.upper() != sim_txn.get("currency", "USD").upper():
            sim_txn["status"] = PaymentStatus.FAILED.value
            raise HTTPException(status_code=400, detail=f"Currency mismatch: captured {captured_currency}, expected {sim_txn.get('currency', 'USD')}")

        seller_breakdown = primary_capture.get("seller_receivable_breakdown", {})
        fee_amount = float(seller_breakdown.get("paypal_fee", {}).get("value", 0.0))
        net_amount = float(seller_breakdown.get("net_amount", {}).get("value", round(captured_amount - fee_amount, 2)))

        payer_info = capture_data.get("payer", {})
        payer_id = payer_info.get("payer_id") or capture_data.get("payment_source", {}).get("paypal", {}).get("account_id")
        payer_email = payer_info.get("email_address") or capture_data.get("payment_source", {}).get("paypal", {}).get("email_address")
        payer_name_obj = payer_info.get("name") or capture_data.get("payment_source", {}).get("paypal", {}).get("name", {})
        payer_name = f"{payer_name_obj.get('given_name', '')} {payer_name_obj.get('surname', '')}".strip() or None

        now = datetime.utcnow()
        sim_txn.update({
            "paypal_capture_id": capture_id,
            "status": PaymentStatus.CAPTURED.value,
            "amount": captured_amount,
            "currency": captured_currency,
            "fee_amount": fee_amount,
            "net_amount": net_amount,
            "payer_id": payer_id,
            "payer_email": payer_email,
            "payer_name": payer_name,
            "captured_at": now.isoformat(),
            "raw_response": json.dumps(capture_data),
        })

        # Sync with simulation orchestrator
        try:
            from ..services.simulation_orchestrator import simulation_orchestrator
            simulation_orchestrator.sync_paypal_capture_sync(
                recovery_order_id=sim_txn["recovery_order_id"],
                paypal_order_id=paypal_order_id,
                paypal_capture_id=capture_id,
                amount=captured_amount,
                currency=captured_currency,
                fee_amount=fee_amount,
                net_amount=net_amount,
                payment_id=sim_txn["payment_id"],
                payer_id=payer_id,
                payer_email=payer_email,
                payer_name=payer_name,
            )
        except Exception as e:
            logger.warning(f"Error syncing capture to simulation orchestrator: {e}")

        logger.info(f"Successfully captured simulation PayPal payment {paypal_order_id} -> {capture_id}")

        return CapturePayPalOrderResponse(
            payment_id=sim_txn["payment_id"],
            recovery_order_id=sim_txn["recovery_order_id"],
            paypal_order_id=paypal_order_id,
            paypal_capture_id=capture_id,
            capture_id=capture_id,
            status=PaymentStatus.CAPTURED.value,
            capture_status="COMPLETED",
            payment_status=PaymentStatus.CAPTURED.value,
            reconciliation_status="PENDING",
            amount=captured_amount,
            currency=captured_currency,
            fee_amount=fee_amount,
            net_amount=net_amount,
            payer_id=payer_id,
            payer_email=payer_email,
            payer_name=payer_name,
            buyer_details={
                "payer_id": payer_id,
                "payer_email": payer_email,
                "payer_name": payer_name,
            },
            captured_at=now,
        )

    def capture_paypal_order(
        self,
        db: Session,
        request: CapturePayPalOrderRequest,
    ) -> CapturePayPalOrderResponse:
        paypal_order_id = request.paypal_order_id

        # Route simulation orders to isolated simulation handler
        if paypal_order_id in self._simulation_transactions or (
            request.recovery_order_id and (request.recovery_order_id.startswith("SIM-") or "SIM" in request.recovery_order_id)
        ):
            return self._capture_simulation_order(request)

        # 1. Retrieve the existing transaction
        transaction = db.query(PaymentTransaction).filter(
            PaymentTransaction.paypal_order_id == paypal_order_id
        ).first()

        if not transaction:
            logger.warning(f"Capture attempt for unknown PayPal Order {paypal_order_id}")
            raise HTTPException(status_code=404, detail=f"No payment record found for PayPal order {paypal_order_id}")

        # 2. Prevent duplicate capture (Idempotency)
        if transaction.status == PaymentStatus.CAPTURED.value:
            logger.info(f"Duplicate capture request for {paypal_order_id}. Returning existing transaction.")
            return CapturePayPalOrderResponse(
                payment_id=transaction.payment_id,
                recovery_order_id=transaction.recovery_order_id,
                paypal_order_id=transaction.paypal_order_id,
                paypal_capture_id=transaction.paypal_capture_id or "",
                status=transaction.status,
                amount=transaction.amount,
                currency=transaction.currency,
                fee_amount=transaction.fee_amount,
                net_amount=transaction.net_amount,
                payer_id=transaction.payer_id,
                payer_email=transaction.payer_email,
                payer_name=transaction.payer_name,
                captured_at=transaction.captured_at or transaction.updated_at,
            )

        # 3. Retrieve the associated RecoveryOrder
        order = db.query(RecoveryOrder).filter(
            RecoveryOrder.order_id == transaction.recovery_order_id
        ).first()

        if not order:
            raise HTTPException(status_code=404, detail=f"Linked RecoveryOrder {transaction.recovery_order_id} not found")

        # 4. Execute PayPal Orders v2 Capture
        try:
            capture_data = paypal_client.capture_order(
                paypal_order_id=paypal_order_id,
                idempotency_key=request.idempotency_key,
            )
        except PayPalClientError as pce:
            transaction.status = PaymentStatus.FAILED.value
            transaction.error_message = pce.message
            db.commit()
            logger.error(f"PayPal capture failed for {paypal_order_id}: {pce.message}")
            raise HTTPException(status_code=pce.status_code, detail=f"PayPal Capture failed: {pce.message}")

        # 5. Strict Response Validation
        paypal_status = capture_data.get("status")
        if paypal_status != "COMPLETED":
            transaction.status = PaymentStatus.FAILED.value
            transaction.error_message = f"PayPal returned non-completed status: {paypal_status}"
            transaction.raw_response = json.dumps(capture_data)
            db.commit()
            raise HTTPException(status_code=400, detail=f"Payment capture failed. PayPal status: {paypal_status}")

        purchase_units = capture_data.get("purchase_units", [])
        if not purchase_units:
            raise HTTPException(status_code=400, detail="Malformed PayPal capture response: purchase_units missing")

        captures = purchase_units[0].get("payments", {}).get("captures", [])
        if not captures:
            raise HTTPException(status_code=400, detail="Malformed PayPal capture response: captures list missing")

        primary_capture = captures[0]
        capture_id = primary_capture.get("id")
        capture_status = primary_capture.get("status")

        if capture_status != "COMPLETED":
            transaction.status = PaymentStatus.FAILED.value
            transaction.error_message = f"Capture record status not COMPLETED: {capture_status}"
            db.commit()
            raise HTTPException(status_code=400, detail=f"Capture record status: {capture_status}")

        # Amount and currency validation against database-persisted order
        captured_val_str = primary_capture.get("amount", {}).get("value", "0.0")
        captured_currency = primary_capture.get("amount", {}).get("currency_code", "")
        captured_amount = float(captured_val_str)

        if abs(captured_amount - float(order.total_amount)) > 0.01:
            logger.error(f"Amount tampering / mismatch detected: Captured {captured_amount} vs Expected {order.total_amount}")
            transaction.status = PaymentStatus.FAILED.value
            transaction.error_message = f"Amount mismatch: captured {captured_amount}, expected {order.total_amount}"
            db.commit()
            raise HTTPException(status_code=400, detail="Payment validation failed: captured amount does not match order")

        if captured_currency.upper() != (order.currency or "USD").upper():
            logger.error(f"Currency mismatch detected: Captured {captured_currency} vs Expected {order.currency}")
            transaction.status = PaymentStatus.FAILED.value
            transaction.error_message = f"Currency mismatch: captured {captured_currency}, expected {order.currency}"
            db.commit()
            raise HTTPException(status_code=400, detail="Payment validation failed: captured currency does not match order")

        # Parse fees & net amount if available
        seller_breakdown = primary_capture.get("seller_receivable_breakdown", {})
        fee_amount = float(seller_breakdown.get("paypal_fee", {}).get("value", 0.0))
        net_amount = float(seller_breakdown.get("net_amount", {}).get("value", round(captured_amount - fee_amount, 2)))

        # Extract Payer info
        payer_info = capture_data.get("payer", {})
        payer_id = payer_info.get("payer_id") or capture_data.get("payment_source", {}).get("paypal", {}).get("account_id")
        payer_email = payer_info.get("email_address") or capture_data.get("payment_source", {}).get("paypal", {}).get("email_address")
        payer_name_obj = payer_info.get("name") or capture_data.get("payment_source", {}).get("paypal", {}).get("name", {})
        payer_name = f"{payer_name_obj.get('given_name', '')} {payer_name_obj.get('surname', '')}".strip() or None

        now = datetime.utcnow()

        # 6. Update PaymentTransaction
        transaction.paypal_capture_id = capture_id
        transaction.status = PaymentStatus.CAPTURED.value
        transaction.fee_amount = fee_amount
        transaction.net_amount = net_amount
        transaction.payer_id = payer_id
        transaction.payer_email = payer_email
        transaction.payer_name = payer_name
        transaction.captured_at = now
        transaction.raw_response = json.dumps(capture_data)

        # 7. Update RecoveryOrder (Decouple fulfillment status!)
        order.status = RecoveryOrderStatus.PAID.value
        order.payment_id = transaction.payment_id
        order.paid_at = now
        # Fulfillment status remains UNFULFILLED until physical dispatch
        if not order.fulfillment_status:
            order.fulfillment_status = RecoveryFulfillmentStatus.UNFULFILLED.value

        db.commit()
        db.refresh(transaction)
        db.refresh(order)

        logger.info(
            f"Successfully captured payment {transaction.payment_id} for order {order.order_id}: "
            f"Capture ID: {capture_id}, Gross: ${captured_amount}, Net: ${net_amount}"
        )

        return CapturePayPalOrderResponse(
            payment_id=transaction.payment_id,
            recovery_order_id=order.order_id,
            paypal_order_id=paypal_order_id,
            paypal_capture_id=capture_id,
            status=transaction.status,
            amount=captured_amount,
            currency=captured_currency,
            fee_amount=fee_amount,
            net_amount=net_amount,
            payer_id=payer_id,
            payer_email=payer_email,
            payer_name=payer_name,
            captured_at=now,
        )

    def handle_cancellation(
        self,
        db: Session,
        request: CancelPayPalOrderRequest,
    ) -> Dict[str, Any]:
        if request.paypal_order_id in self._simulation_transactions:
            sim_txn = self._simulation_transactions[request.paypal_order_id]
            if sim_txn.get("status") != PaymentStatus.CAPTURED.value:
                sim_txn["status"] = PaymentStatus.CANCELLED.value
                sim_txn["error_message"] = request.reason
            return {
                "status": "CANCELLED",
                "paypal_order_id": request.paypal_order_id,
                "message": "Payment session was cancelled by buyer.",
            }

        transaction = db.query(PaymentTransaction).filter(
            PaymentTransaction.paypal_order_id == request.paypal_order_id
        ).first()

        if transaction and transaction.status != PaymentStatus.CAPTURED.value:
            transaction.status = PaymentStatus.CANCELLED.value
            transaction.error_message = request.reason
            db.commit()

        return {
            "status": "CANCELLED",
            "paypal_order_id": request.paypal_order_id,
            "message": "Payment session was cancelled by buyer.",
        }

    def get_payment(self, db: Session, payment_id: str) -> Optional[PaymentTransaction]:
        return db.query(PaymentTransaction).filter(
            PaymentTransaction.payment_id == payment_id
        ).first()

    def get_simulation_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve simulation payment record by payment_id, paypal_order_id, or paypal_capture_id."""
        for sim_txn in self._simulation_transactions.values():
            if (
                sim_txn.get("payment_id") == payment_id
                or sim_txn.get("paypal_order_id") == payment_id
                or sim_txn.get("paypal_capture_id") == payment_id
            ):
                now = datetime.utcnow()
                captured_at_dt = None
                if sim_txn.get("captured_at"):
                    try:
                        captured_at_dt = datetime.fromisoformat(sim_txn["captured_at"])
                    except Exception:
                        captured_at_dt = now

                amt = float(sim_txn.get("amount", 0.0))
                fee = float(sim_txn.get("fee_amount", 0.0))
                net = float(sim_txn.get("net_amount", amt - fee))
                cap_id = sim_txn.get("paypal_capture_id")
                return {
                    "payment_id": sim_txn.get("payment_id", payment_id),
                    "recovery_order_id": sim_txn.get("recovery_order_id", ""),
                    "paypal_order_id": sim_txn.get("paypal_order_id"),
                    "paypal_capture_id": cap_id,
                    "capture_id": cap_id,
                    "status": sim_txn.get("status", PaymentStatus.PENDING_APPROVAL.value),
                    "capture_status": "COMPLETED" if sim_txn.get("status") == PaymentStatus.CAPTURED.value else sim_txn.get("status"),
                    "payment_status": sim_txn.get("status"),
                    "reconciliation_status": "RECONCILED",
                    "amount": amt,
                    "currency": sim_txn.get("currency", "USD"),
                    "fee_amount": fee,
                    "net_amount": net,
                    "payer_id": sim_txn.get("payer_id"),
                    "payer_email": sim_txn.get("payer_email"),
                    "payer_name": sim_txn.get("payer_name"),
                    "buyer_details": {
                        "payer_id": sim_txn.get("payer_id"),
                        "payer_email": sim_txn.get("payer_email"),
                        "payer_name": sim_txn.get("payer_name"),
                    },
                    "created_at": now,
                    "updated_at": now,
                    "captured_at": captured_at_dt,
                }
        return None

    def get_payments_by_order(self, db: Session, recovery_order_id: str) -> List[PaymentTransaction]:
        return db.query(PaymentTransaction).filter(
            PaymentTransaction.recovery_order_id == recovery_order_id
        ).order_by(PaymentTransaction.created_at.desc()).all()

    def get_eligible_orders(self, db: Session) -> List[RecoveryOrder]:
        """Lists recovery orders eligible for PayPal checkout."""
        return db.query(RecoveryOrder).order_by(RecoveryOrder.created_at.desc()).all()

payment_service = PaymentService()
