from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class PayPalClientConfig(BaseModel):
    client_id: str
    currency: str = "USD"
    mode: str = "sandbox"
    is_mock: bool = False
    is_configured: bool = True

class CreatePayPalOrderRequest(BaseModel):
    recovery_order_id: str = Field(..., description="Unique ID of the eligible recovery order")
    idempotency_key: Optional[str] = Field(None, description="Optional client idempotency key to prevent duplicate orders")
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None

class CreatePayPalOrderResponse(BaseModel):
    payment_id: str
    paypal_order_id: str
    recovery_order_id: str
    amount: float
    currency: str
    status: str
    approval_url: Optional[str] = None

class CapturePayPalOrderRequest(BaseModel):
    paypal_order_id: str = Field(..., description="PayPal Order ID returned by create-order and approved by buyer")
    recovery_order_id: Optional[str] = Field(None, description="Optional recovery order ID verification")
    idempotency_key: Optional[str] = None

class CapturePayPalOrderResponse(BaseModel):
    payment_id: str
    recovery_order_id: str
    paypal_order_id: str
    paypal_capture_id: str
    status: str
    amount: float
    currency: str
    fee_amount: float = 0.0
    net_amount: float = 0.0
    payer_id: Optional[str] = None
    payer_email: Optional[str] = None
    payer_name: Optional[str] = None
    captured_at: datetime
    # Enhanced visibility and verification fields
    capture_id: Optional[str] = None
    capture_status: Optional[str] = None
    payment_status: Optional[str] = None
    reconciliation_status: Optional[str] = "PENDING"
    buyer_details: Optional[Dict[str, Any]] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.capture_id:
            self.capture_id = self.paypal_capture_id
        if not self.capture_status:
            self.capture_status = self.status
        if not self.payment_status:
            self.payment_status = self.status
        if self.buyer_details is None:
            self.buyer_details = {
                "payer_id": self.payer_id,
                "payer_email": self.payer_email,
                "payer_name": self.payer_name,
            }

class CancelPayPalOrderRequest(BaseModel):
    paypal_order_id: str
    recovery_order_id: Optional[str] = None
    reason: Optional[str] = "Buyer cancelled payment session"

class PaymentTransactionResponse(BaseModel):
    payment_id: str
    recovery_order_id: str
    paypal_order_id: Optional[str] = None
    paypal_capture_id: Optional[str] = None
    status: str
    amount: float
    currency: str
    fee_amount: float
    net_amount: float
    payer_id: Optional[str] = None
    payer_email: Optional[str] = None
    payer_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    captured_at: Optional[datetime] = None
    # Enhanced visibility and verification fields
    capture_id: Optional[str] = None
    capture_status: Optional[str] = None
    payment_status: Optional[str] = None
    reconciliation_status: Optional[str] = "RECONCILED"
    buyer_details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

    def model_post_init(self, __context: Any) -> None:
        if not self.capture_id and self.paypal_capture_id:
            self.capture_id = self.paypal_capture_id
        if not self.capture_status:
            self.capture_status = "COMPLETED" if self.status in ("CAPTURED", "PAID") else self.status
        if not self.payment_status:
            self.payment_status = self.status
        if self.buyer_details is None:
            self.buyer_details = {
                "payer_id": self.payer_id,
                "payer_email": self.payer_email,
                "payer_name": self.payer_name,
            }

class RecoveryOrderCreate(BaseModel):
    sku_id: str
    product_name: str
    source_store_id: str
    channel: str = "DISCOUNT_MARKETPLACE"
    quantity: int
    unit_price: float
    currency: str = "USD"
    buyer_id: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_email: Optional[str] = None

class RecoveryOrderResponse(BaseModel):
    order_id: str
    sku_id: str
    product_name: str
    source_store_id: str
    channel: str
    quantity: int
    unit_price: float
    total_amount: float
    currency: str
    status: str
    fulfillment_status: str
    payment_id: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_email: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True
