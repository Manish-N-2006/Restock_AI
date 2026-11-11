from fastapi import APIRouter, Depends
from . import inventory, risk, recovery, health, demand, decision, logistics, transfers, outcomes, agent, history, workflow, authorization, simulation
from ..auth.router import router as auth_router
from ..auth.service import require_authenticated_session
from ..payments.router import router as payments_router

_protected = [Depends(require_authenticated_session)]

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

api_router.include_router(inventory.router, prefix="/api", tags=["Inventory"], dependencies=_protected)
api_router.include_router(risk.router, prefix="/api", tags=["Risk"], dependencies=_protected)
api_router.include_router(recovery.router, prefix="/api", tags=["Recovery"], dependencies=_protected)
api_router.include_router(demand.router, prefix="/api/demand", tags=["Demand"], dependencies=_protected)
api_router.include_router(decision.router, prefix="/api/decision", tags=["Decision"], dependencies=_protected)
api_router.include_router(logistics.router, prefix="/api/logistics", tags=["Logistics"], dependencies=_protected)
api_router.include_router(transfers.router, prefix="/api/transfers", tags=["Transfers"], dependencies=_protected)
api_router.include_router(outcomes.router, tags=["Outcomes"], dependencies=_protected)
api_router.include_router(agent.router, tags=["Agent"], dependencies=_protected)
api_router.include_router(history.router, tags=["History"], dependencies=_protected)
api_router.include_router(workflow.router, tags=["Workflow"], dependencies=_protected)
api_router.include_router(authorization.router, prefix="/api/authorization", tags=["Authorization"], dependencies=_protected)
api_router.include_router(payments_router, prefix="/api", tags=["PayPal Payments"], dependencies=_protected)
api_router.include_router(simulation.router, dependencies=_protected)
