from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any

class HistorySearchResult(BaseModel):
    transfer_id: str
    sku_id: str
    source_store_id: str
    destination_store_id: Optional[str] = None
    action: Optional[str] = None
    actual_net_recovery: Optional[float] = None
    recovery_accuracy_percentage: Optional[float] = None
    actual_units_sold: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class HistorySearchResponse(BaseModel):
    total: int
    results: List[HistorySearchResult]
    
    model_config = ConfigDict(from_attributes=True)

class HistorySummaryResponse(BaseModel):
    total_indexed_transfers: int
    total_finalized_outcomes: int
    total_units_moved: int
    total_actual_net_recovery: float
    average_recovery_accuracy: Optional[float] = None
    average_sell_through_rate: Optional[float] = None
    transfer_count_by_action: Dict[str, int]
    transfer_count_by_partner: Dict[str, int]

    model_config = ConfigDict(from_attributes=True)

class OpenSearchHealthResponse(BaseModel):
    configured: bool
    available: bool
    index: str

    model_config = ConfigDict(from_attributes=True)
