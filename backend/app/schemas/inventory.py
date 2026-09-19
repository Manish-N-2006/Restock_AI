from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from typing import Optional

class InventoryBase(BaseModel):
    sku_id: str
    product_name: str
    store_id: str
    quantity: int
    cost_price: float
    selling_price: float
    expiry_date: datetime
    daily_sales_7d: float
    temperature_class: str
    return_allowed: bool = False
    supplier_return_value: Optional[float] = None
    reserved_quantity: int = 0
    
    @property
    def available_quantity(self) -> int:
        return max(self.quantity - self.reserved_quantity, 0)

class InventoryCreate(InventoryBase):
    pass

class Inventory(InventoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
