from fastapi import APIRouter
from . import inventory, risk, recovery, health, demand, decision, logistics, transfers, outcomes, agent, history, workflow, authorization

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(inventory.router, prefix="/api", tags=["Inventory"])
api_router.include_router(risk.router, prefix="/api", tags=["Risk"])
api_router.include_router(recovery.router, prefix="/api", tags=["Recovery"])
api_router.include_router(demand.router, prefix="/api/demand", tags=["Demand"])
api_router.include_router(decision.router, prefix="/api/decision", tags=["Decision"])
api_router.include_router(logistics.router, prefix="/api/logistics", tags=["Logistics"])
api_router.include_router(transfers.router, prefix="/api/transfers", tags=["Transfers"])
api_router.include_router(outcomes.router, tags=["Outcomes"])
api_router.include_router(agent.router, tags=["Agent"])

api_router.include_router(history.router, tags=["History"])

api_router.include_router(workflow.router, tags=["Workflow"])

api_router.include_router(authorization.router, prefix="/api/authorization", tags=["Authorization"])
