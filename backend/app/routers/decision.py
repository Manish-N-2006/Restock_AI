from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..schemas.decision import DecisionResponse, ActionComparisonResponse, DecisionSummaryResponse
from ..services import decision_engine
from ..authorization.dependencies import require_permission
from ..authorization.actions import Action

router = APIRouter()

@router.get("/summary", response_model=DecisionSummaryResponse, dependencies=[Depends(require_permission(Action.VIEW_DECISION, "Decision"))])
def get_decision_summary(db: Session = Depends(get_db)):
    return decision_engine.get_decision_summary(db)

@router.get("/all", response_model=List[DecisionResponse], dependencies=[Depends(require_permission(Action.VIEW_DECISION, "Decision"))])
def get_all_decisions(db: Session = Depends(get_db)):
    return decision_engine.get_all_decisions(db)

@router.get("/{sku_id}/actions", response_model=ActionComparisonResponse, dependencies=[Depends(require_permission(Action.VIEW_DECISION, "Decision"))])
def get_action_comparison(
    sku_id: str,
    store_id: str = Query(..., description="The store ID containing the at-risk inventory"),
    db: Session = Depends(get_db)
):
    decision = decision_engine.evaluate_decision(db, sku_id, store_id)
    return ActionComparisonResponse(
        sku_id=sku_id,
        store_id=store_id,
        actions=decision.actions
    )

@router.get("/{sku_id}", response_model=DecisionResponse, dependencies=[Depends(require_permission(Action.VIEW_DECISION, "Decision"))])
def get_decision(
    sku_id: str,
    store_id: str = Query(..., description="The store ID containing the at-risk inventory"),
    db: Session = Depends(get_db)
):
    return decision_engine.evaluate_decision(db, sku_id, store_id)
