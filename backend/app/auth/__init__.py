from .models import LoginAttemptBucket, RevokedSession
from .router import router
from .service import (
    CSRF_HEADER_NAME,
    DEFAULT_SESSION_COOKIE_NAME,
    DEMO_STORE_SCOPE,
    DEMO_USER_ID,
    DEMO_USER_ROLE,
    HOST_SESSION_COOKIE_NAME,
    MAX_SESSION_TTL_MINUTES,
    MIN_SESSION_SECRET_LENGTH,
    create_session_token,
    derive_csrf_token,
    get_session_cookie_name,
    is_production,
    require_authenticated_session,
    reset_auth_runtime_state,
    validate_production_configuration,
    validate_session_secret,
    validate_websocket_origin,
    verify_session_token,
    verify_websocket_session,
)

# Backwards-compatible alias
SESSION_COOKIE_NAME = DEFAULT_SESSION_COOKIE_NAME

__all__ = [
    "router",
    "LoginAttemptBucket",
    "RevokedSession",
    "CSRF_HEADER_NAME",
    "DEFAULT_SESSION_COOKIE_NAME",
    "HOST_SESSION_COOKIE_NAME",
    "SESSION_COOKIE_NAME",
    "DEMO_USER_ID",
    "DEMO_USER_ROLE",
    "DEMO_STORE_SCOPE",
    "MIN_SESSION_SECRET_LENGTH",
    "MAX_SESSION_TTL_MINUTES",
    "create_session_token",
    "derive_csrf_token",
    "get_session_cookie_name",
    "is_production",
    "require_authenticated_session",
    "reset_auth_runtime_state",
    "validate_production_configuration",
    "validate_session_secret",
    "validate_websocket_origin",
    "verify_session_token",
    "verify_websocket_session",
]
