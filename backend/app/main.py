import logging
import os
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import Depends, FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from .auth.service import (
    get_allowed_origins,
    is_production,
    require_authenticated_session,
    validate_production_configuration,
)
from .database import check_database_connection
from .office.router import handle_office_websocket, router as office_router
from .routers import api_router
from .services.data_loader import init_db, seed_data

logger = logging.getLogger("restockai.main")


def get_cors_origins() -> List[str]:
    """Build explicit CORS allowed origin list from environment configuration."""
    return get_allowed_origins()


def get_cors_origin_regex() -> Optional[str]:
    """Disabled in production so credentialed CORS enforces exact FRONTEND_URL."""
    if is_production():
        return None
    regex = os.getenv("CORS_ORIGIN_REGEX", "").strip()
    return regex or None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate production security settings, ensure schema exists idempotently, and seed if empty."""
    if is_production():
        validate_production_configuration()

    try:
        init_db()
        if os.getenv("RESTOCKAI_RUN_SEED_ON_STARTUP", "true").strip().lower() in ("true", "1", "yes"):
            seed_data()
        db_ok = check_database_connection()
        logger.info("ReStockAI startup completed (database_connected=%s).", db_ok)
    except Exception as exc:
        logger.error("Database initialization during startup failed: %s", exc)
        if is_production():
            raise
    yield


def create_app() -> FastAPI:
    """Application factory disabling OpenAPI/Swagger in production and tightening CORS."""
    prod = is_production()
    application = FastAPI(
        title="ReStockAI",
        version="2.0.0",
        lifespan=lifespan,
        docs_url=None if prod else "/docs",
        redoc_url=None if prod else "/redoc",
        openapi_url=None if prod else "/openapi.json",
    )

    cors_origins = get_cors_origins()
    cors_origin_regex = get_cors_origin_regex()

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=cors_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Accept"],
    )

    application.include_router(api_router)
    application.include_router(office_router, dependencies=[Depends(require_authenticated_session)])

    @application.websocket("/ws/office")
    async def websocket_office_endpoint(websocket: WebSocket):
        await handle_office_websocket(websocket)

    @application.websocket("/ws")
    async def websocket_alias_endpoint(websocket: WebSocket):
        await handle_office_websocket(websocket)

    return application


app = create_app()
