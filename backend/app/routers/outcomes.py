from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..schemas.outcome import (
    OutcomeResponse,
    RecordSalesRequest,
    RecordFinancialsRequest,
    OutcomeSummaryResponse
)
from ..authorization.dependencies import require_permission
from ..authorization.actions import Action
from ..services.outcome_engine import (
    create_outcome_from_transfer,
    record_actual_sales,
    record_actual_financials,
    finalize_outcome,
    get_outcome,
    list_outcomes,
    get_outcome_summary,
    build_outcome_response
)

router = APIRouter(prefix="/api/outcomes", tags=["Outcomes"])

@router.post("/from-transfer/{transfer_id}", response_model=OutcomeResponse, dependencies=[Depends(require_permission(Action.MODIFY_FINALIZED_OUTCOME, "Outcome"))])
def api_create_outcome(transfer_id: str, db: Session = Depends(get_db)):
    """Initialize outcome tracking for a completed transfer."""
    outcome = create_outcome_from_transfer(db, transfer_id)
    return build_outcome_response(outcome)

@router.post("/{outcome_id}/record-sales", response_model=OutcomeResponse, dependencies=[Depends(require_permission(Action.MODIFY_FINALIZED_OUTCOME, "Outcome"))])
def api_record_sales(outcome_id: str, req: RecordSalesRequest, db: Session = Depends(get_db)):
    """Record actual units sold."""
    outcome = record_actual_sales(db, outcome_id, req.actual_units_sold)
    return build_outcome_response(outcome)

@router.post("/{outcome_id}/record-financials", response_model=OutcomeResponse, dependencies=[Depends(require_permission(Action.MODIFY_FINALIZED_OUTCOME, "Outcome"))])
def api_record_financials(outcome_id: str, req: RecordFinancialsRequest, db: Session = Depends(get_db)):
    """Record actual recovered value and costs."""
    outcome = record_actual_financials(db, outcome_id, req.actual_recovered_value, req.actual_logistics_cost, req.actual_handling_cost)
    return build_outcome_response(outcome)

@router.post("/{outcome_id}/finalize", response_model=OutcomeResponse, dependencies=[Depends(require_permission(Action.MODIFY_FINALIZED_OUTCOME, "Outcome"))])
def api_finalize_outcome(outcome_id: str, db: Session = Depends(get_db)):
    """Finalize outcome and calculate deterministic metrics."""
    outcome = finalize_outcome(db, outcome_id)
    return build_outcome_response(outcome)

@router.get("/summary", response_model=OutcomeSummaryResponse, dependencies=[Depends(require_permission(Action.VIEW_OUTCOME, "Outcome"))])
def api_get_outcome_summary(db: Session = Depends(get_db)):
    """Get network-wide historical recovery metrics."""
    return get_outcome_summary(db)

@router.get("/{outcome_id}", response_model=OutcomeResponse, dependencies=[Depends(require_permission(Action.VIEW_OUTCOME, "Outcome"))])
def api_get_outcome(outcome_id: str, db: Session = Depends(get_db)):
    """Fetch an outcome by ID."""
    outcome = get_outcome(db, outcome_id)
    return build_outcome_response(outcome)

@router.get("", response_model=List[OutcomeResponse], dependencies=[Depends(require_permission(Action.VIEW_OUTCOME, "Outcome"))])
def api_list_outcomes(
    sku_id: Optional[str] = None,
    transfer_id: Optional[str] = None,
    destination_store_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List outcomes with optional filters."""
    outcomes = list_outcomes(db, sku_id, transfer_id, destination_store_id, status)
    return [build_outcome_response(o) for o in outcomes]
