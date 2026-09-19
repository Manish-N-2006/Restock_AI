from fastapi import APIRouter, HTTPException
from ..schemas.recovery import RecoveryEvaluateRequest, RecoveryEvaluateResponse
from ..services import recovery_engine

router = APIRouter()

@router.post("/recovery/evaluate", response_model=RecoveryEvaluateResponse)
def evaluate_recovery(request: RecoveryEvaluateRequest):
    if request.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
        
    return recovery_engine.evaluate_recovery_action(request)
