from sqlalchemy import Column, Integer, String, Float, Boolean
from ..database import Base

class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String, unique=True, index=True)
    store_name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    address = Column(String)
    supports_cold_chain = Column(Boolean, default=False)
