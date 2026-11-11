import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from ..database import Base

class RecoveryOrderStatus(str, enum.Enum):
    CREATED = "CREATED"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"

class RecoveryFulfillmentStatus(str, enum.Enum):
    UNFULFILLED = "UNFULFILLED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class RecoveryOrder(Base):
    """
    Coordinated commercial recovery order entity.
    Represents an inventory recovery transaction (e.g. discount marketplace sale,
    B2B liquidation, bulk buyer purchase).
    Payment status is strictly decoupled from fulfillment status.
    """
    __tablename__ = "recovery_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    sku_id = Column(String, index=True)
    product_name = Column(String)
    source_store_id = Column(String, index=True)
    channel = Column(String, default="DISCOUNT_MARKETPLACE")  # DISCOUNT_MARKETPLACE, B2B_WHOLESALE, LIQUIDATION
    quantity = Column(Integer)
    unit_price = Column(Float)
    total_amount = Column(Float)
    currency = Column(String, default="USD")
    
    # Buyer Information
    buyer_id = Column(String, nullable=True)
    buyer_name = Column(String, nullable=True)
    buyer_email = Column(String, nullable=True)
    
    # Decoupled Statuses
    status = Column(String, default=RecoveryOrderStatus.CREATED.value, index=True)  # Payment / order lifecycle
    fulfillment_status = Column(String, default=RecoveryFulfillmentStatus.UNFULFILLED.value, index=True)
    
    # Associated payment reference
    payment_id = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    fulfilled_at = Column(DateTime, nullable=True)


class RecoveryOffer(Base):
    """
    Active commercial recovery offer or markdown campaign.
    """
    __tablename__ = "recovery_offers"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(String, unique=True, index=True)
    sku_id = Column(String, index=True)
    product_name = Column(String)
    source_store_id = Column(String, index=True)
    discount_pct = Column(Float)
    offer_price = Column(Float)
    original_price = Column(Float)
    available_quantity = Column(Integer)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
