import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class PaymentStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"

class PaymentTransaction(Base):
    """
    Persistent record of a payment transaction.
    References the coordinated RecoveryOrder, stores PayPal v2 order and capture IDs,
    records idempotency tokens, and provides an immutable audit log.
    """
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String, unique=True, index=True)  # e.g. "PAY-3A4B5C6D"
    recovery_order_id = Column(String, ForeignKey("recovery_orders.order_id"), index=True)
    
    # PayPal identifiers
    paypal_order_id = Column(String, unique=True, index=True, nullable=True)
    paypal_capture_id = Column(String, unique=True, index=True, nullable=True)
    
    # Financial fields
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    fee_amount = Column(Float, default=0.0)
    net_amount = Column(Float, default=0.0)
    
    # State & Idempotency
    status = Column(String, default=PaymentStatus.INITIATED.value, index=True)
    idempotency_key = Column(String, unique=True, index=True, nullable=True)
    
    # Payer Info (from PayPal capture response)
    payer_id = Column(String, nullable=True)
    payer_email = Column(String, nullable=True)
    payer_name = Column(String, nullable=True)
    
    # Audit trail
    payment_method = Column(String, default="PAYPAL_SANDBOX")
    error_message = Column(Text, nullable=True)
    raw_response = Column(Text, nullable=True)  # Full JSON payload for reconciliation & compliance
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    captured_at = Column(DateTime, nullable=True)
