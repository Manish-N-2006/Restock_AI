from sqlalchemy import Column, Integer, String, Float, Boolean
from ..database import Base

class LogisticsPartner(Base):
    __tablename__ = "logistics_partners"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(String, unique=True, index=True)
    partner_name = Column(String)
    cost_per_km = Column(Float)
    base_cost = Column(Float)
    average_eta_minutes = Column(Integer)
    capacity_units = Column(Integer)
    supports_cold_chain = Column(Boolean)
