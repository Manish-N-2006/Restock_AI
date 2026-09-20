from fastapi import APIRouter
from typing import Dict, Any
from ..schemas.workflow import WorkflowAnalyzeRequest, WorkflowExecuteRequest
from ..services.orchestration_engine import run_recovery_analysis, run_complete_recovery_workflow, get_workflow_status
from ..authorization.dependencies import require_permission
from ..authorization.actions import Action
from fastapi import Depends

router = APIRouter(prefix="/api/workflow", tags=["Workflow"])

@router.post("/analyze", response_model=Dict[str, Any], dependencies=[Depends(require_permission(Action.ANALYZE_WORKFLOW, "Workflow"))])
def analyze_workflow(req: WorkflowAnalyzeRequest):
    return run_recovery_analysis(req.sku_id, req.source_store_id)

@router.post("/execute", response_model=Dict[str, Any], dependencies=[Depends(require_permission(Action.ANALYZE_WORKFLOW, "Workflow"))])
def execute_workflow(req: WorkflowExecuteRequest):
    return run_complete_recovery_workflow(
        sku_id=req.sku_id,
        source_store_id=req.source_store_id,
        actual_units_sold=req.actual_units_sold,
        actual_recovered_value=req.actual_recovered_value,
        actual_logistics_cost=req.actual_logistics_cost,
        actual_handling_cost=req.actual_handling_cost
    )

@router.get("/status/{transfer_id}", response_model=Dict[str, Any], dependencies=[Depends(require_permission(Action.ANALYZE_WORKFLOW, "Workflow"))])
def get_status(transfer_id: str):
    return get_workflow_status(transfer_id)
