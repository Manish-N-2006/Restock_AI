import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .config import paypal_settings
from .schemas import (
    PayPalClientConfig,
    CreatePayPalOrderRequest,
    CreatePayPalOrderResponse,
    CapturePayPalOrderRequest,
    CapturePayPalOrderResponse,
    CancelPayPalOrderRequest,
    PaymentTransactionResponse,
    RecoveryOrderResponse,
    RecoveryOrderCreate,
)
from .service import payment_service
from ..models.commerce import RecoveryOrder, RecoveryOrderStatus, RecoveryFulfillmentStatus

router = APIRouter(prefix="/payments", tags=["PayPal Payments"])

@router.get("/config", response_model=PayPalClientConfig)
def get_paypal_config():
    """
    Returns PayPal client configuration for the official JavaScript SDK.
    Never exposes client_secret.
    """
    if paypal_settings.is_configured:
        return PayPalClientConfig(
            client_id=paypal_settings.client_id,
            currency=paypal_settings.currency,
            mode=paypal_settings.mode,
            is_mock=False,
            is_configured=True,
        )
    elif paypal_settings.allow_mock:
        return PayPalClientConfig(
            client_id="sb",
            currency=paypal_settings.currency,
            mode=paypal_settings.mode,
            is_mock=True,
            is_configured=False,
        )
    else:
        return PayPalClientConfig(
            client_id="",
            currency=paypal_settings.currency,
            mode=paypal_settings.mode,
            is_mock=False,
            is_configured=False,
        )

@router.post("/paypal/create-order", response_model=CreatePayPalOrderResponse)
def create_paypal_order(
    request: CreatePayPalOrderRequest,
    db: Session = Depends(get_db),
):
    """
    Creates a PayPal Orders API v2 order for a verified RecoveryOrder.
    Amount is strictly calculated on the server from the database record.
    """
    if not paypal_settings.is_configured and not paypal_settings.allow_mock:
        raise HTTPException(
            status_code=503,
            detail="PayPal Sandbox credentials missing. Set RESTOCKAI_PAYPAL_CLIENT_ID and RESTOCKAI_PAYPAL_CLIENT_SECRET in .env.",
        )
    return payment_service.create_paypal_order(db=db, request=request)

@router.post("/paypal/capture", response_model=CapturePayPalOrderResponse)
def capture_paypal_order(
    request: CapturePayPalOrderRequest,
    db: Session = Depends(get_db),
):
    """
    Captures payment for a buyer-approved PayPal order.
    Validates status, amount, and currency before marking the order as PAID.
    Fulfillment status remains decoupled and UNFULFILLED.
    """
    return payment_service.capture_paypal_order(db=db, request=request)

@router.post("/paypal/cancel")
def cancel_paypal_order(
    request: CancelPayPalOrderRequest,
    db: Session = Depends(get_db),
):
    """
    Handles payment cancellation initiated by buyer in the PayPal checkout interface.
    """
    return payment_service.handle_cancellation(db=db, request=request)

@router.get("/{payment_id}", response_model=PaymentTransactionResponse)
def get_payment_details(
    payment_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves full transaction status and audit record for a given payment ID.
    """
    txn = payment_service.get_payment(db=db, payment_id=payment_id)
    if txn:
        return txn
    sim_txn = payment_service.get_simulation_payment(payment_id=payment_id)
    if sim_txn:
        return sim_txn
    raise HTTPException(status_code=404, detail=f"Payment transaction {payment_id} not found")

@router.get("/order/{recovery_order_id}", response_model=List[PaymentTransactionResponse])
def get_order_payment_history(
    recovery_order_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves all payment transactions associated with a given RecoveryOrder.
    """
    return payment_service.get_payments_by_order(db=db, recovery_order_id=recovery_order_id)

@router.get("/orders/eligible", response_model=List[RecoveryOrderResponse])
def get_eligible_recovery_orders(
    db: Session = Depends(get_db),
):
    """
    Lists recovery orders in the system for checkout selection.
    """
    return payment_service.get_eligible_orders(db=db)

@router.get("/orders/{order_id}", response_model=RecoveryOrderResponse)
def get_recovery_order(
    order_id: str,
    db: Session = Depends(get_db),
):
    order = db.query(RecoveryOrder).filter(RecoveryOrder.order_id == order_id).first()
    if not order:
        if order_id.startswith("SIM-") or "SIM" in order_id:
            from datetime import datetime
            from ..services.simulation_orchestrator import simulation_orchestrator
            sim_data = simulation_orchestrator.get_order_data(order_id)
            if sim_data:
                return RecoveryOrderResponse(
                    id=99999,
                    order_id=order_id,
                    sku_id=sim_data.get("sku_id", "YOG-001"),
                    product_name=sim_data.get("product_name", "Greek Yogurt 500g"),
                    source_store_id="STORE_A",
                    channel="DISCOUNT_MARKETPLACE",
                    quantity=sim_data.get("quantity", 104),
                    unit_price=sim_data.get("unit_price", 1.80),
                    total_amount=sim_data.get("total_amount", 187.20),
                    currency=sim_data.get("currency", "USD"),
                    buyer_id="BUYER-METRO-01",
                    buyer_name=sim_data.get("buyer_name", "Metro Retail Discount Mart"),
                    buyer_email=sim_data.get("buyer_email", "buyer@metroretail.example.com"),
                    status=sim_data.get("status", "CREATED"),
                    fulfillment_status=sim_data.get("fulfillment_status", "UNFULFILLED"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
        raise HTTPException(status_code=404, detail=f"RecoveryOrder {order_id} not found")
    return order

@router.post("/orders/create", response_model=RecoveryOrderResponse)
def create_recovery_order(
    data: RecoveryOrderCreate,
    db: Session = Depends(get_db),
):
    """
    Creates a commercial RecoveryOrder (e.g. from Commerce Agent or discount strategy).
    """
    order_id = f"REC-ORD-{uuid.uuid4().hex[:8].upper()}"
    total = round(data.quantity * data.unit_price, 2)
    order = RecoveryOrder(
        order_id=order_id,
        sku_id=data.sku_id,
        product_name=data.product_name,
        source_store_id=data.source_store_id,
        channel=data.channel,
        quantity=data.quantity,
        unit_price=data.unit_price,
        total_amount=total,
        currency=data.currency,
        buyer_id=data.buyer_id,
        buyer_name=data.buyer_name,
        buyer_email=data.buyer_email,
        status=RecoveryOrderStatus.CREATED.value,
        fulfillment_status=RecoveryFulfillmentStatus.UNFULFILLED.value,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order
