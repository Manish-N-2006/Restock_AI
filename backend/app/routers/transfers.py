from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..schemas.transfer import (
    TransferOrderRecommendationCreate,
    TransferOrderCreate,
    TransferOrderResponse,
    TransferSummaryResponse
)
from ..services import transfer_engine

router = APIRouter()

@router.post("/from-recommendation", response_model=TransferOrderResponse)
def create_transfer_from_recommendation(
    request: TransferOrderRecommendationCreate,
    db: Session = Depends(get_db)
):
    return transfer_engine.create_transfer_from_recommendation(
        db, request.sku_id, request.source_store_id
    )

@router.post("", response_model=TransferOrderResponse)
def create_manual_transfer(
    request: TransferOrderCreate,
    db: Session = Depends(get_db)
):
    return transfer_engine.create_manual_transfer(
        db, request.sku_id, request.source_store_id, request.destination_store_id, request.quantity
    )

@router.post("/{transfer_id}/approve", response_model=TransferOrderResponse)
def approve_transfer(
    transfer_id: str = Path(...),
    db: Session = Depends(get_db)
):
    return transfer_engine.approve_transfer(db, transfer_id)

@router.post("/{transfer_id}/assign", response_model=TransferOrderResponse)
def assign_transfer(
    transfer_id: str = Path(...),
    db: Session = Depends(get_db)
):
    return transfer_engine.assign_transfer(db, transfer_id)

@router.post("/{transfer_id}/pickup", response_model=TransferOrderResponse)
def pickup_transfer(
    transfer_id: str = Path(...),
    db: Session = Depends(get_db)
):
    return transfer_engine.mark_pickup_pending(db, transfer_id)

@router.post("/{transfer_id}/start-transit", response_model=TransferOrderResponse)
def start_transit_transfer(
    transfer_id: str = Path(...),
    db: Session = Depends(get_db)
):
    return transfer_engine.start_transfer(db, transfer_id)

@router.post("/{transfer_id}/deliver", response_model=TransferOrderResponse)
def deliver_transfer(
    transfer_id: str = Path(...),
    db: Session = Depends(get_db)
):
    return transfer_engine.mark_delivered(db, transfer_id)

@router.post("/{transfer_id}/complete", response_model=TransferOrderResponse)
def complete_transfer(
    transfer_id: str = Path(...),
    db: Session = Depends(get_db)
):
    return transfer_engine.complete_transfer(db, transfer_id)

@router.post("/{transfer_id}/cancel", response_model=TransferOrderResponse)
def cancel_transfer(
    transfer_id: str = Path(...),
    db: Session = Depends(get_db)
):
    return transfer_engine.cancel_transfer(db, transfer_id)

@router.get("/summary", response_model=TransferSummaryResponse)
def get_transfers_summary(db: Session = Depends(get_db)):
    return transfer_engine.get_transfer_summary(db)

@router.get("/{transfer_id}", response_model=TransferOrderResponse)
def get_transfer(
    transfer_id: str = Path(...),
    db: Session = Depends(get_db)
):
    return transfer_engine.get_transfer(db, transfer_id)

@router.get("", response_model=List[TransferOrderResponse])
def list_transfers(
    status: Optional[str] = None,
    sku_id: Optional[str] = None,
    source_store_id: Optional[str] = None,
    destination_store_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    return transfer_engine.list_transfers(db, status, sku_id, source_store_id, destination_store_id)
