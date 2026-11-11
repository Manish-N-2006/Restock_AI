from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from ..office.service import office_service
from .service import (
    DEFAULT_SESSION_COOKIE_NAME,
    DEMO_USER_ID,
    DEMO_USER_ROLE,
    HOST_SESSION_COOKIE_NAME,
    check_login_rate_limit,
    clear_failed_logins,
    create_session_token,
    derive_csrf_token,
    enforce_json_content_type,
    ensure_auth_configured,
    extract_session_cookie,
    get_client_ip,
    get_cookie_samesite,
    get_session_cookie_name,
    record_failed_login,
    revoke_session_token,
    should_use_secure_cookie,
    validate_csrf_header,
    validate_request_origin,
    verify_demo_password,
    verify_session_token,
)

router = APIRouter()


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response):
    validate_request_origin(request)
    await enforce_json_content_type(request)
    ensure_auth_configured()

    client_key = get_client_ip(request)
    check_login_rate_limit(client_key)

    if not verify_demo_password(body.password):
        record_failed_login(client_key)
        raise HTTPException(status_code=401, detail="Invalid demo password")

    clear_failed_logins(client_key)
    token, claims = create_session_token()

    secure = should_use_secure_cookie(request)
    samesite = get_cookie_samesite(secure)
    cookie_name = get_session_cookie_name(secure)
    ttl_seconds = max(1, int(claims["exp"]) - int(claims["iat"]))

    response.set_cookie(
        key=cookie_name,
        value=token,
        max_age=ttl_seconds,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/",
    )

    return {
        "authenticated": True,
        "user": DEMO_USER_ID,
        "role": DEMO_USER_ROLE,
        "expires_at": claims["exp"],
        "csrf_token": derive_csrf_token(claims["jti"]),
    }


@router.post("/logout")
async def logout(request: Request, response: Response):
    validate_request_origin(request)
    await enforce_json_content_type(request)

    token = extract_session_cookie(request.cookies, request)
    active_claims = verify_session_token(token)
    if active_claims:
        validate_csrf_header(request, active_claims)

    revoked_jti = revoke_session_token(token)
    if revoked_jti:
        await office_service.close_sessions_by_jti(revoked_jti)

    secure = should_use_secure_cookie(request)
    samesite = get_cookie_samesite(secure)
    for cookie_name in (get_session_cookie_name(secure), DEFAULT_SESSION_COOKIE_NAME):
        if cookie_name == HOST_SESSION_COOKIE_NAME and not secure:
            continue
        response.delete_cookie(
            key=cookie_name,
            path="/",
            httponly=True,
            secure=secure,
            samesite=samesite,
        )

    return {
        "authenticated": False,
        "message": "Logged out successfully",
    }


@router.get("/session")
def get_session(request: Request):
    token = extract_session_cookie(request.cookies, request)
    claims = verify_session_token(token)
    if not claims:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "authenticated": True,
        "user": claims["sub"],
        "role": claims["role"],
        "expires_at": claims["exp"],
        "csrf_token": derive_csrf_token(claims["jti"]),
    }
