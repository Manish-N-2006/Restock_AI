from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models.inventory import Inventory
from ..schemas import inventory as inventory_schema

router = APIRouter()

@router.get("/inventory", response_model=List[inventory_schema.Inventory])
def read_inventory(store_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Inventory)
    if store_id:
        query = query.filter(Inventory.store_id == store_id)
    return query.all()

@router.get("/inventory/{sku_id}", response_model=List[inventory_schema.Inventory])
def read_inventory_by_sku(sku_id: str, store_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Inventory).filter(Inventory.sku_id == sku_id)
    if store_id:
        query = query.filter(Inventory.store_id == store_id)
    
    records = query.all()
    if not records:
        raise HTTPException(status_code=404, detail="SKU not found")
    return records
