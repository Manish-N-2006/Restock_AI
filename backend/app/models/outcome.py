from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..database import Base

class OutcomeStatus(enum.Enum):
    PENDING = "PENDING"
    RECORDED = "RECORDED"
    FINALIZED = "FINALIZED"

class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(Integer, primary_key=True, index=True)
    outcome_id = Column(String, unique=True, index=True)
    transfer_id = Column(String, ForeignKey("transfer_orders.transfer_id"), unique=True, index=True)
    sku_id = Column(String, index=True)
    source_store_id = Column(String, index=True)
    destination_store_id = Column(String, index=True)
    transferred_quantity = Column(Integer)

    # Prediction Snapshot
    predicted_units_sold = Column(Integer, nullable=True)
    predicted_recovered_value = Column(Float, nullable=True)
    predicted_logistics_cost = Column(Float, nullable=True)
    predicted_handling_cost = Column(Float, nullable=True)
    predicted_net_recovery = Column(Float, nullable=True)

    # Actual Results
    actual_units_sold = Column(Integer, nullable=True)
    actual_unsold_units = Column(Integer, nullable=True)
    actual_recovered_value = Column(Float, nullable=True)
    actual_logistics_cost = Column(Float, nullable=True)
    actual_handling_cost = Column(Float, nullable=True)
    actual_net_recovery = Column(Float, nullable=True)

    # Derived Metrics
    recovery_variance = Column(Float, nullable=True)
    recovery_percentage = Column(Float, nullable=True)
    unit_sales_variance = Column(Integer, nullable=True)
    logistics_cost_variance = Column(Float, nullable=True)
    recovery_accuracy_percentage = Column(Float, nullable=True)
    sell_through_rate = Column(Float, nullable=True)

    # Status and Timing
    outcome_status = Column(Enum(OutcomeStatus), default=OutcomeStatus.PENDING, index=True)
    outcome_recorded_at = Column(DateTime, default=datetime.utcnow)
    finalized_at = Column(DateTime, nullable=True)

    events = relationship("OutcomeEvent", back_populates="outcome", cascade="all, delete-orphan")

class OutcomeEvent(Base):
    __tablename__ = "outcome_events"

    id = Column(Integer, primary_key=True, index=True)
    outcome_id = Column(String, ForeignKey("outcomes.outcome_id"), index=True)
    event_type = Column(String)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    outcome = relationship("Outcome", back_populates="events")
