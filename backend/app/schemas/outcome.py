from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from .decision import RecoveryActionType

class OutcomePredictionSnapshot(BaseModel):
    predicted_units_sold: Optional[int] = None
    predicted_recovered_value: Optional[float] = None
    predicted_logistics_cost: Optional[float] = None
    predicted_handling_cost: Optional[float] = None
    predicted_net_recovery: Optional[float] = None

class OutcomeActualsSnapshot(BaseModel):
    actual_units_sold: Optional[int] = None
    actual_unsold_units: Optional[int] = None
    actual_recovered_value: Optional[float] = None
    actual_logistics_cost: Optional[float] = None
    actual_handling_cost: Optional[float] = None
    actual_net_recovery: Optional[float] = None

class OutcomeMetricsSnapshot(BaseModel):
    recovery_variance: Optional[float] = None
    recovery_percentage: Optional[float] = None
    unit_sales_variance: Optional[int] = None
    logistics_cost_variance: Optional[float] = None
    recovery_accuracy_percentage: Optional[float] = None
    sell_through_rate: Optional[float] = None

class OutcomeEventResponse(BaseModel):
    event_type: str
    message: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class OutcomeResponse(BaseModel):
    outcome_id: str
    transfer_id: str
    sku_id: str
    source_store_id: str
    destination_store_id: str
    transferred_quantity: int
    
    prediction: OutcomePredictionSnapshot
    actual: OutcomeActualsSnapshot
    metrics: OutcomeMetricsSnapshot
    
    status: str = Field(alias="outcome_status")
    outcome_recorded_at: datetime
    finalized_at: Optional[datetime] = None
    events: List[OutcomeEventResponse] = []
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class RecordSalesRequest(BaseModel):
    actual_units_sold: int = Field(..., ge=0)

class RecordFinancialsRequest(BaseModel):
    actual_recovered_value: float = Field(..., ge=0)
    actual_logistics_cost: float = Field(..., ge=0)
    actual_handling_cost: float = Field(..., ge=0)

class OutcomeSummaryResponse(BaseModel):
    total_completed_transfers: int
    total_finalized_outcomes: int
    total_units_transferred: int
    total_units_sold: int
    total_units_unsold: int
    total_recovered_value: float
    total_actual_logistics_cost: float
    total_actual_net_recovery: float
    total_predicted_net_recovery: float
    total_recovery_variance: float
    average_recovery_accuracy: Optional[float] = None
    average_sell_through_rate: Optional[float] = None
