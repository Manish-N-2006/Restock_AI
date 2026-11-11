import base64
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import secrets
import threading
import time
from typing import Any, Dict, List, Literal, Mapping, Optional, Tuple
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, WebSocket

from ..database import SessionLocal
from ..payments.config import paypal_settings
from .models import LoginAttemptBucket, RevokedSession

logger = logging.getLogger(__name__)

DEFAULT_SESSION_COOKIE_NAME = "restockai_session"
HOST_SESSION_COOKIE_NAME = "__Host-restockai_session"
CSRF_HEADER_NAME = "X-CSRF-Token"

DEMO_USER_ID = "demo-manager"
DEMO_USER_ROLE = "MANAGER"
DEMO_STORE_SCOPE = "*"

MIN_SESSION_SECRET_LENGTH = 32
DEFAULT_SESSION_TTL_MINUTES = 60
MAX_SESSION_TTL_MINUTES = 480

DEFAULT_LOGIN_MAX_ATTEMPTS = 5
DEFAULT_LOGIN_GLOBAL_MAX_ATTEMPTS = 25
DEFAULT_LOGIN_WINDOW_SECONDS = 300
DEFAULT_MAX_RATE_LIMIT_BUCKETS = 2000

_db_write_lock = threading.Lock()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def is_production() -> bool:
    return os.getenv("RESTOCKAI_ENV", "development").strip().lower() == "production"


def get_demo_password() -> str:
    return os.getenv("RESTOCKAI_DEMO_PASSWORD", "")


def get_session_secret() -> str:
    return os.getenv("RESTOCKAI_SESSION_SECRET", "").strip()


def validate_session_secret(
    secret: Optional[str] = None,
    demo_password: Optional[str] = None,
) -> str:
    """Validate that the session signing secret meets minimum length and differs from the demo password."""
    resolved_secret = get_session_secret() if secret is None else secret.strip()
    resolved_password = get_demo_password() if demo_password is None else demo_password

    if not resolved_secret:
        raise ValueError("RESTOCKAI_SESSION_SECRET must be configured.")
    if len(resolved_secret) < MIN_SESSION_SECRET_LENGTH:
        raise ValueError(
            f"RESTOCKAI_SESSION_SECRET must be at least {MIN_SESSION_SECRET_LENGTH} characters."
        )
    if resolved_password and hmac.compare_digest(
        resolved_secret.encode("utf-8"),
        resolved_password.encode("utf-8"),
    ):
        raise ValueError("RESTOCKAI_SESSION_SECRET must not match RESTOCKAI_DEMO_PASSWORD.")
    return resolved_secret


def get_session_ttl_minutes() -> int:
    raw = os.getenv("RESTOCKAI_SESSION_TTL_MINUTES", str(DEFAULT_SESSION_TTL_MINUTES)).strip()
    try:
        ttl = int(raw)
    except ValueError as exc:
        raise ValueError("RESTOCKAI_SESSION_TTL_MINUTES must be an integer.") from exc

    if ttl < 1 or ttl > MAX_SESSION_TTL_MINUTES:
        raise ValueError(
            f"RESTOCKAI_SESSION_TTL_MINUTES must be between 1 and {MAX_SESSION_TTL_MINUTES}."
        )
    return ttl


def get_login_max_attempts() -> int:
    raw = os.getenv("RESTOCKAI_LOGIN_MAX_ATTEMPTS", str(DEFAULT_LOGIN_MAX_ATTEMPTS)).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_LOGIN_MAX_ATTEMPTS


def get_login_global_max_attempts() -> int:
    raw = os.getenv(
        "RESTOCKAI_LOGIN_GLOBAL_MAX_ATTEMPTS",
        str(DEFAULT_LOGIN_GLOBAL_MAX_ATTEMPTS),
    ).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_LOGIN_GLOBAL_MAX_ATTEMPTS


def get_login_window_seconds() -> int:
    raw = os.getenv("RESTOCKAI_LOGIN_WINDOW_SECONDS", str(DEFAULT_LOGIN_WINDOW_SECONDS)).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_LOGIN_WINDOW_SECONDS


def get_max_rate_limit_buckets() -> int:
    raw = os.getenv("RESTOCKAI_MAX_RATE_LIMIT_BUCKETS", str(DEFAULT_MAX_RATE_LIMIT_BUCKETS)).strip()
    try:
        return max(10, int(raw))
    except ValueError:
        return DEFAULT_MAX_RATE_LIMIT_BUCKETS


def get_trusted_proxy_hops() -> int:
    """
    Number of trusted reverse-proxy hops appending to X-Forwarded-For from the right.
    On Render Web Services, set RESTOCKAI_TRUSTED_PROXY_HOPS=1 so Render's edge proxy
    entry (rightmost) is read while client-prepended entries on the left are ignored.
    """
    raw = os.getenv("RESTOCKAI_TRUSTED_PROXY_HOPS", "0").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _get_trusted_proxy_networks() -> List[ipaddress._BaseNetwork]:
    raw = os.getenv("RESTOCKAI_TRUSTED_PROXY_CIDRS", "").strip()
    networks: List[ipaddress._BaseNetwork] = []
    if not raw:
        return networks
    for item in raw.split(","):
        cleaned = item.strip()
        if not cleaned:
            continue
        try:
            networks.append(ipaddress.ip_network(cleaned, strict=False))
        except ValueError:
            logger.warning("Ignoring invalid RESTOCKAI_TRUSTED_PROXY_CIDRS entry: %s", cleaned)
    return networks


def _is_trusted_proxy_peer(peer_host: str) -> bool:
    if not peer_host:
        return False
    if peer_host == "testclient" and os.getenv("RESTOCKAI_ENV", "development").strip().lower() == "test":
        return True
    try:
        addr = ipaddress.ip_address(peer_host)
    except ValueError:
        return False

    configured_nets = _get_trusted_proxy_networks()
    if configured_nets:
        return any(addr in net for net in configured_nets)
    return addr.is_private or addr.is_loopback or addr.is_link_local


def _is_localhost_origin(origin: str) -> bool:
    parsed = urlsplit(origin.strip())
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def get_allowed_origins() -> List[str]:
    """Return exact allowed origins from FRONTEND_URL / CORS_ORIGINS (plus dev localhost outside prod)."""
    origins: List[str] = []
    raw_lists = [
        os.getenv("CORS_ORIGINS", ""),
        os.getenv("RESTOCKAI_CORS_ORIGINS", ""),
        os.getenv("FRONTEND_URL", ""),
    ]
    for raw in raw_lists:
        for item in raw.split(","):
            cleaned = item.strip().rstrip("/")
            if cleaned and cleaned != "*" and cleaned not in origins:
                origins.append(cleaned)

    if not is_production():
        dev_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5180",
            "http://127.0.0.1:5180",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ]
        for origin in dev_origins:
            if origin not in origins:
                origins.append(origin)
    return origins


def validate_production_configuration() -> None:
    """Fail-closed validation executed during production startup."""
    if not get_demo_password():
        raise RuntimeError("RESTOCKAI_DEMO_PASSWORD is required in production.")

    validate_session_secret()
    get_session_ttl_minutes()

    frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if not frontend_url or not frontend_url.lower().startswith("https://") or "*" in frontend_url:
        raise RuntimeError("FRONTEND_URL must be an explicit https:// origin in production.")
    if _is_localhost_origin(frontend_url):
        raise RuntimeError("FRONTEND_URL cannot point to localhost in production.")

    paypal_settings.validate_production_callbacks()


def should_use_secure_cookie(request: Optional[Any] = None) -> bool:
    """Enable Secure + __Host- cookie mode in production or whenever HTTPS is active."""
    if is_production():
        return True
    frontend_url = os.getenv("FRONTEND_URL", "").strip().lower()
    if frontend_url.startswith("https://"):
        return True
    if request is not None:
        if getattr(request.url, "scheme", "") in ("https", "wss"):
            return True
        forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
        if forwarded_proto in ("https", "wss"):
            return True
    return False


def get_session_cookie_name(secure: bool) -> str:
    return HOST_SESSION_COOKIE_NAME if secure else DEFAULT_SESSION_COOKIE_NAME


def extract_session_cookie(
    cookies: Mapping[str, str],
    request_or_ws: Optional[Any] = None,
) -> Optional[str]:
    secure = should_use_secure_cookie(request_or_ws)
    if secure:
        return cookies.get(HOST_SESSION_COOKIE_NAME)
    return cookies.get(DEFAULT_SESSION_COOKIE_NAME) or cookies.get(HOST_SESSION_COOKIE_NAME)


def get_cookie_samesite(secure: bool) -> Literal["none", "lax"]:
    """
    Use SameSite=None over HTTPS so separate-origin Render Static Site -> Web Service
    requests and WSS upgrades carry HttpOnly cookies; use Lax on local HTTP.
    """
    return "none" if secure else "lax"


def resolve_client_rate_limit_key(request: Request) -> Tuple[str, bool]:
    """
    Resolve a rate-limit bucket key without trusting spoofable left-most X-Forwarded-For values.
    Returns (bucket_key, is_trusted_client_ip).
    """
    peer_host = request.client.host.strip() if request.client and request.client.host else ""
    trusted_hops = get_trusted_proxy_hops()

    if trusted_hops <= 0:
        if not peer_host or peer_host.lower() == "unknown":
            return "untrusted:global", False
        try:
            ipaddress.ip_address(peer_host)
            return f"ip:{peer_host}", True
        except ValueError:
            if peer_host == "testclient" and not is_production():
                return f"peer:{peer_host}", True
            return "untrusted:global", False

    if not _is_trusted_proxy_peer(peer_host):
        return "untrusted:global", False

    raw_xff = request.headers.get("x-forwarded-for", "").strip()
    if not raw_xff:
        return "untrusted:global", False

    parts = [p.strip() for p in raw_xff.split(",") if p.strip()]
    if len(parts) < trusted_hops:
        return "untrusted:global", False

    client_ip = parts[-trusted_hops]
    try:
        ipaddress.ip_address(client_ip)
    except ValueError:
        return "untrusted:global", False

    return f"ip:{client_ip}", True


def get_client_ip(request: Request) -> str:
    bucket_key, _ = resolve_client_rate_limit_key(request)
    return bucket_key


def _parse_timestamps(raw: str, cutoff: float) -> List[float]:
    try:
        parsed = json.loads(raw or "[]")
        if not isinstance(parsed, list):
            return []
        return [float(ts) for ts in parsed if isinstance(ts, (int, float)) and float(ts) > cutoff]
    except (ValueError, TypeError):
        return []


def _cleanup_expired_rate_limit_buckets(db, now: float) -> None:
    db.query(LoginAttemptBucket).filter(LoginAttemptBucket.window_expires_at <= now).delete(
        synchronize_session=False
    )


def _enforce_rate_limit_capacity(db, exclude_keys: set[str]) -> None:
    max_buckets = get_max_rate_limit_buckets()
    current_count = db.query(LoginAttemptBucket).count()
    if current_count < max_buckets:
        return

    excess = current_count - max_buckets + 1
    oldest_rows = (
        db.query(LoginAttemptBucket.bucket_key)
        .filter(~LoginAttemptBucket.bucket_key.in_(exclude_keys))
        .order_by(LoginAttemptBucket.updated_at.asc())
        .limit(excess)
        .all()
    )
    keys_to_delete = [row[0] for row in oldest_rows]
    if keys_to_delete:
        db.query(LoginAttemptBucket).filter(
            LoginAttemptBucket.bucket_key.in_(keys_to_delete)
        ).delete(synchronize_session=False)


def check_login_rate_limit(client_key: str) -> None:
    max_attempts = get_login_max_attempts()
    global_max = get_login_global_max_attempts()
    window_seconds = get_login_window_seconds()
    now = time.time()
    cutoff = now - window_seconds

    with _db_write_lock:
        with SessionLocal() as db:
            _cleanup_expired_rate_limit_buckets(db, now)
            dirty = False

            checks = [(client_key, max_attempts), ("__global__", global_max)]
            for key, limit in checks:
                row = db.query(LoginAttemptBucket).filter(LoginAttemptBucket.bucket_key == key).first()
                if not row:
                    continue
                timestamps = _parse_timestamps(row.attempt_timestamps, cutoff)
                if not timestamps:
                    db.delete(row)
                    dirty = True
                    continue
                if len(timestamps) >= limit:
                    retry_after = max(1, int((timestamps[0] + window_seconds) - now))
                    if dirty:
                        db.commit()
                    else:
                        db.commit()
                    raise HTTPException(
                        status_code=429,
                        detail="Too many failed login attempts. Please try again later.",
                        headers={"Retry-After": str(retry_after)},
                    )

            db.commit()


def record_failed_login(client_key: str) -> None:
    window_seconds = get_login_window_seconds()
    now = time.time()
    cutoff = now - window_seconds

    with _db_write_lock:
        with SessionLocal() as db:
            _cleanup_expired_rate_limit_buckets(db, now)

            keys_to_update = [client_key] if client_key == "__global__" else [client_key, "__global__"]
            for key in keys_to_update:
                row = db.query(LoginAttemptBucket).filter(LoginAttemptBucket.bucket_key == key).first()
                if row:
                    timestamps = _parse_timestamps(row.attempt_timestamps, cutoff)
                    timestamps.append(now)
                    row.attempt_timestamps = json.dumps(timestamps)
                    row.window_expires_at = timestamps[0] + window_seconds
                    row.updated_at = now
                else:
                    _enforce_rate_limit_capacity(db, {"__global__", client_key})
                    db.add(
                        LoginAttemptBucket(
                            bucket_key=key,
                            attempt_timestamps=json.dumps([now]),
                            window_expires_at=now + window_seconds,
                            updated_at=now,
                        )
                    )
            db.commit()


def clear_failed_logins(client_key: str) -> None:
    with _db_write_lock:
        with SessionLocal() as db:
            db.query(LoginAttemptBucket).filter(LoginAttemptBucket.bucket_key == client_key).delete(
                synchronize_session=False
            )
            db.commit()


def verify_demo_password(provided_password: str) -> bool:
    expected = get_demo_password()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Demo authentication is not configured on the server.",
        )
    if not provided_password:
        return False
    return hmac.compare_digest(
        provided_password.encode("utf-8"),
        expected.encode("utf-8"),
    )


def ensure_auth_configured() -> None:
    if not get_demo_password():
        raise HTTPException(
            status_code=503,
            detail="Demo authentication is not configured on the server.",
        )
    try:
        validate_session_secret()
        get_session_ttl_minutes()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def derive_csrf_token(jti: str) -> str:
    secret = validate_session_secret()
    digest = hmac.new(secret.encode("utf-8"), f"csrf:{jti}".encode("utf-8"), hashlib.sha256).digest()
    return _b64url_encode(digest)


def create_session_token(ttl_seconds: Optional[int] = None) -> tuple[str, Dict[str, Any]]:
    try:
        secret = validate_session_secret()
        effective_ttl = ttl_seconds if ttl_seconds is not None else get_session_ttl_minutes() * 60
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    now = int(time.time())
    payload: Dict[str, Any] = {
        "sub": DEMO_USER_ID,
        "role": DEMO_USER_ROLE,
        "store_scope": DEMO_STORE_SCOPE,
        "jti": secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + int(effective_ttl),
    }
    header = {"alg": "HS256", "typ": "JWT"}

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}", payload


def _is_jti_revoked(jti: str) -> bool:
    now = time.time()
    with SessionLocal() as db:
        db.query(RevokedSession).filter(RevokedSession.expires_at <= now).delete(synchronize_session=False)
        existing = (
            db.query(RevokedSession)
            .filter(RevokedSession.jti == jti, RevokedSession.expires_at > now)
            .first()
        )
        db.commit()
        return existing is not None


def _decode_signed_token(
    token: Optional[str],
    verify_exp: bool = True,
    check_revocation: bool = True,
) -> Optional[Dict[str, Any]]:
    if not token or not isinstance(token, str):
        return None
    try:
        secret = validate_session_secret()
    except ValueError:
        return None

    parts = token.split(".")
    if len(parts) != 3 or not all(parts):
        return None

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    expected_sig_b64 = _b64url_encode(expected_sig)

    if not hmac.compare_digest(expected_sig_b64, sig_b64):
        return None

    try:
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None

    if not isinstance(header, dict) or not isinstance(payload, dict):
        return None
    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        return None

    if payload.get("sub") != DEMO_USER_ID or payload.get("role") != DEMO_USER_ROLE:
        return None

    jti = payload.get("jti")
    exp = payload.get("exp")
    if not isinstance(jti, str) or not jti or not isinstance(exp, (int, float)):
        return None

    now = time.time()
    if verify_exp and now >= float(exp):
        return None

    if check_revocation and _is_jti_revoked(jti):
        return None

    return payload


def verify_session_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    return _decode_signed_token(token, verify_exp=True, check_revocation=True)


def revoke_session_token(token: Optional[str]) -> Optional[str]:
    payload = _decode_signed_token(token, verify_exp=False, check_revocation=False)
    if not payload:
        return None

    jti = payload["jti"]
    exp = float(payload["exp"])
    now = time.time()

    if exp > now:
        with _db_write_lock:
            with SessionLocal() as db:
                db.query(RevokedSession).filter(RevokedSession.expires_at <= now).delete(
                    synchronize_session=False
                )
                db.merge(RevokedSession(jti=jti, expires_at=exp, revoked_at=now))
                db.commit()
    return jti


def _extract_origin_from_referer(referer: str) -> Optional[str]:
    parsed = urlsplit(referer.strip())
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
    return None


def _is_origin_in_allowlist(origin: str) -> bool:
    normalized = origin.strip().rstrip("/").lower()
    if not normalized or normalized == "null":
        return False
    allowed = {o.strip().rstrip("/").lower() for o in get_allowed_origins()}
    return normalized in allowed


def validate_request_origin(request: Request) -> None:
    """
    Verify request Origin (or Referer in non-production when Origin is omitted).
    In production, missing or untrusted Origin headers are strictly rejected (HTTP 403).
    """
    origin = request.headers.get("origin", "").strip()
    if origin:
        if not _is_origin_in_allowlist(origin):
            raise HTTPException(status_code=403, detail="Untrusted request origin.")
        return

    if is_production():
        raise HTTPException(status_code=403, detail="Origin header is required in production.")

    referer = request.headers.get("referer", "").strip()
    if referer:
        ref_origin = _extract_origin_from_referer(referer)
        if not ref_origin or not _is_origin_in_allowlist(ref_origin):
            raise HTTPException(status_code=403, detail="Untrusted request referer.")


def validate_websocket_origin(websocket: WebSocket) -> bool:
    """Validate WebSocket handshake Origin before room admission."""
    origin = websocket.headers.get("origin", "").strip()
    if origin:
        return _is_origin_in_allowlist(origin)
    if is_production():
        return False
    return True


async def enforce_json_content_type(request: Request) -> None:
    """Reject non-JSON form/text payloads and ensure body-bearing mutations use application/json."""
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type:
        if content_type != "application/json":
            raise HTTPException(
                status_code=415,
                detail="Content-Type must be application/json.",
            )
        return

    body = await request.body()
    if body:
        raise HTTPException(
            status_code=415,
            detail="Content-Type: application/json header is required for request payloads.",
        )


def validate_csrf_header(request: Request, claims: Dict[str, Any]) -> None:
    provided = request.headers.get(CSRF_HEADER_NAME, "").strip()
    expected = derive_csrf_token(claims["jti"])
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token.")


async def require_authenticated_session(request: Request) -> Dict[str, Any]:
    token = extract_session_cookie(request.cookies, request)
    claims = verify_session_token(token)
    if not claims:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        validate_request_origin(request)
        await enforce_json_content_type(request)
        validate_csrf_header(request, claims)

    return claims


def verify_websocket_session(websocket: WebSocket) -> Optional[Dict[str, Any]]:
    token = extract_session_cookie(websocket.cookies, websocket)
    return verify_session_token(token)


def reset_auth_runtime_state() -> None:
    """Clear persisted auth revocations and login attempt buckets (for automated tests)."""
    with _db_write_lock:
        try:
            with SessionLocal() as db:
                db.query(RevokedSession).delete(synchronize_session=False)
                db.query(LoginAttemptBucket).delete(synchronize_session=False)
                db.commit()
        except Exception as exc:
            logger.debug("Ignoring auth table cleanup before DB init: %s", exc)
