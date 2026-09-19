from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from enum import Enum

class TransferStatus(str, Enum):
    CREATED = "CREATED"
    APPROVED = "APPROVED"
    ASSIGNED = "ASSIGNED"
    PICKUP_PENDING = "PICKUP_PENDING"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

class TransferEventResponse(BaseModel):
    id: int
    transfer_id: str
    from_status: Optional[TransferStatus] = None
    to_status: TransferStatus
    event_type: str
    message: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class TransferOrderBase(BaseModel):
    sku_id: str
    source_store_id: str
    destination_store_id: str
    quantity: int

class TransferOrderCreate(TransferOrderBase):
    pass

class TransferOrderRecommendationCreate(BaseModel):
    sku_id: str
    source_store_id: str

class TransferOrderResponse(TransferOrderBase):
    id: int
    transfer_id: str
    product_name: str
    status: TransferStatus
    
    logistics_partner_id: Optional[str] = None
    logistics_partner_name: Optional[str] = None
    distance_km: Optional[float] = None
    estimated_delivery_cost: Optional[float] = None
    estimated_eta_minutes: Optional[int] = None
    
    expected_net_recovery: Optional[float] = None
    logistics_adjusted_net_recovery: Optional[float] = None
    
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime] = None
    assigned_at: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None
    in_transit_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    events: List[TransferEventResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

class TransferSummaryResponse(BaseModel):
    total_transfers: int
    created: int
    approved: int
    assigned: int
    pickup_pending: int
    in_transit: int
    delivered: int
    completed: int
    cancelled: int
    failed: int
    total_units_transferred: int
    total_estimated_logistics_cost: float
    total_expected_net_recovery: float
