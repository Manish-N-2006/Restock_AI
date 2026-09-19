from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..schemas.demand import DemandMatchResponse, BestMatchResponse, DemandSummaryResponse
from ..services import demand_engine

router = APIRouter()

@router.get("/candidates/{sku_id}", response_model=DemandMatchResponse)
def get_demand_candidates(
    sku_id: str, 
    source_store_id: str = Query(..., description="The store ID containing the at-risk inventory"),
    minimum_risk_level: str = Query("HIGH", description="Minimum risk level required to seek a match"),
    db: Session = Depends(get_db)
):
    return demand_engine.find_destination_candidates(db, sku_id, source_store_id, minimum_risk_level)

@router.get("/best-match/{sku_id}", response_model=BestMatchResponse)
def get_best_match(
    sku_id: str, 
    source_store_id: str = Query(..., description="The store ID containing the at-risk inventory"),
    db: Session = Depends(get_db)
):
    return demand_engine.get_best_match(db, sku_id, source_store_id)

@router.get("/summary", response_model=DemandSummaryResponse)
def get_demand_summary(db: Session = Depends(get_db)):
    return demand_engine.get_demand_summary(db)
