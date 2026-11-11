import os
from fastapi import APIRouter, Depends, HTTPException
from ..auth.service import require_authenticated_session
from ..database import check_database_connection, get_database_dialect

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ReStockAI",
    }


@router.get("/health/details", dependencies=[Depends(require_authenticated_session)])
@router.get("/api/health", dependencies=[Depends(require_authenticated_session)])
def detailed_health_check():
    db_connected = check_database_connection()
    if not db_connected:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed.",
        )

    return {
        "status": "ok",
        "service": "ReStockAI",
        "environment": os.getenv("RESTOCKAI_ENV", "development").lower(),
        "database": {
            "connected": True,
            "dialect": get_database_dialect(),
        },
        "opensearch_fallback": os.getenv("RESTOCKAI_OPENSEARCH_FALLBACK", "false").lower() == "true",
    }
