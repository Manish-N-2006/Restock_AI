from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any

class WorkflowAnalyzeRequest(BaseModel):
    sku_id: str
    source_store_id: str
    
    model_config = ConfigDict(from_attributes=True)

class WorkflowExecuteRequest(BaseModel):
    sku_id: str
    source_store_id: str
    actual_units_sold: Optional[int] = 0
    actual_recovered_value: Optional[float] = 0.0
    actual_logistics_cost: Optional[float] = 0.0
    actual_handling_cost: Optional[float] = 0.0
    partner_id: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
