from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any

class WorkflowAnalyzeRequest(BaseModel):
    sku_id: str
    source_store_id: str
    
    model_config = ConfigDict(from_attributes=True)

class WorkflowExecuteRequest(BaseModel):
    sku_id: str
    source_store_id: str
    actual_units_sold: int
    actual_recovered_value: float
    actual_logistics_cost: float
    actual_handling_cost: float
    
    model_config = ConfigDict(from_attributes=True)
