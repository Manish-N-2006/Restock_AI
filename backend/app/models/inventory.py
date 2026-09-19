from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from ..database import Base

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(String, index=True)
    product_name = Column(String)
    store_id = Column(String, index=True)
    quantity = Column(Integer)
    cost_price = Column(Float)
    selling_price = Column(Float)
    expiry_date = Column(DateTime)
    daily_sales_7d = Column(Float)
    temperature_class = Column(String)
    created_at = Column(DateTime)
    return_allowed = Column(Boolean, default=False)
    supplier_return_value = Column(Float, nullable=True)
    reserved_quantity = Column(Integer, default=0)
