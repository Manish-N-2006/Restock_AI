from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..database import Base

class TransferStatus(enum.Enum):
    CREATED = "CREATED"
    APPROVED = "APPROVED"
    ASSIGNED = "ASSIGNED"
    PICKUP_PENDING = "PICKUP_PENDING"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

class TransferOrder(Base):
    __tablename__ = "transfer_orders"

    id = Column(Integer, primary_key=True, index=True)
    transfer_id = Column(String, unique=True, index=True)
    sku_id = Column(String, index=True)
    product_name = Column(String)
    source_store_id = Column(String, index=True)
    destination_store_id = Column(String, index=True)
    quantity = Column(Integer)
    status = Column(Enum(TransferStatus), default=TransferStatus.CREATED, index=True)
    
    # Logistics details snapshot
    logistics_partner_id = Column(String, nullable=True)
    logistics_partner_name = Column(String, nullable=True)
    distance_km = Column(Float, nullable=True)
    estimated_delivery_cost = Column(Float, nullable=True)
    estimated_eta_minutes = Column(Integer, nullable=True)
    
    # Economics snapshot
    expected_net_recovery = Column(Float, nullable=True)
    logistics_adjusted_net_recovery = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    picked_up_at = Column(DateTime, nullable=True)
    in_transit_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    events = relationship("TransferEvent", back_populates="transfer_order", cascade="all, delete-orphan")

class TransferEvent(Base):
    __tablename__ = "transfer_events"

    id = Column(Integer, primary_key=True, index=True)
    transfer_id = Column(String, ForeignKey("transfer_orders.transfer_id"), index=True)
    from_status = Column(Enum(TransferStatus), nullable=True)
    to_status = Column(Enum(TransferStatus))
    event_type = Column(String)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    transfer_order = relationship("TransferOrder", back_populates="events")
