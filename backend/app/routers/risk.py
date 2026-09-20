from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.risk import RiskResponse, RiskSummaryResponse
from ..services import risk_engine
from ..authorization.dependencies import require_permission
from ..authorization.actions import Action

router = APIRouter()

@router.get("/risk", response_model=RiskResponse, dependencies=[Depends(require_permission(Action.VIEW_RISK, "Risk"))])
def get_risk(db: Session = Depends(get_db)):
    return risk_engine.evaluate_all_risks(db)

@router.get("/risk/summary", response_model=RiskSummaryResponse, dependencies=[Depends(require_permission(Action.VIEW_RISK, "Risk"))])
def get_risk_summary(db: Session = Depends(get_db)):
    return risk_engine.get_risk_summary(db)
