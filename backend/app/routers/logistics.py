from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..schemas.logistics import (
    LogisticsOptionsResponse,
    BestLogisticsResponse,
    IntegratedRecommendationResponse,
    LogisticsSummaryResponse
)
from ..services import logistics_engine

router = APIRouter()

@router.get("/options", response_model=LogisticsOptionsResponse)
def get_logistics_options(
    sku_id: str,
    source_store_id: str,
    destination_store_id: str,
    transfer_quantity: int = Query(..., gt=0),
    db: Session = Depends(get_db)
):
    return logistics_engine.evaluate_logistics_options(
        db, sku_id, source_store_id, destination_store_id, transfer_quantity
    )

@router.get("/best", response_model=BestLogisticsResponse)
def get_best_logistics_partner(
    sku_id: str,
    source_store_id: str,
    destination_store_id: str,
    transfer_quantity: int = Query(..., gt=0),
    db: Session = Depends(get_db)
):
    return logistics_engine.get_best_logistics_partner(
        db, sku_id, source_store_id, destination_store_id, transfer_quantity
    )

@router.get("/recommend/{sku_id}", response_model=IntegratedRecommendationResponse)
def get_integrated_recommendation(
    sku_id: str,
    source_store_id: str = Query(..., description="The store ID containing the at-risk inventory"),
    db: Session = Depends(get_db)
):
    return logistics_engine.get_integrated_recommendation(db, sku_id, source_store_id)

@router.get("/summary", response_model=LogisticsSummaryResponse)
def get_logistics_summary(db: Session = Depends(get_db)):
    return logistics_engine.get_logistics_summary(db)
