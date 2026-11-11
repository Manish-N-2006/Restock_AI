import os
from pathlib import Path
from urllib.parse import urlsplit
from pydantic import BaseModel
from dotenv import load_dotenv

# Search and load .env from workspace root and backend folder without overriding Render platform vars
_current_file = Path(__file__).resolve()
_workspace_root = _current_file.parent.parent.parent.parent
load_dotenv(_workspace_root / ".env", override=False)
load_dotenv(_current_file.parent.parent.parent / ".env", override=False)


def _is_localhost_url(url: str) -> bool:
    parsed = urlsplit(url.strip())
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def _is_production_env() -> bool:
    return os.getenv("RESTOCKAI_ENV", "development").strip().lower() == "production"


def _resolve_frontend_callback_url(env_var: str, suffix: str) -> str:
    is_prod = _is_production_env()
    explicit = os.getenv(env_var, "").strip()
    if explicit:
        if is_prod and (not explicit.lower().startswith("https://") or _is_localhost_url(explicit)):
            raise ValueError(f"{env_var} must be a non-localhost https:// URL in production.")
        return explicit

    frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if frontend_url:
        if is_prod and (not frontend_url.lower().startswith("https://") or _is_localhost_url(frontend_url)):
            raise ValueError("FRONTEND_URL must be a non-localhost https:// URL in production.")
        return f"{frontend_url}{suffix}"

    if is_prod:
        raise ValueError(
            f"{env_var} or an https:// FRONTEND_URL is required in production (localhost fallback is disabled)."
        )
    return f"http://localhost:5173{suffix}"


class PayPalSettings(BaseModel):
    client_id: str = (os.getenv("RESTOCKAI_PAYPAL_CLIENT_ID") or os.getenv("PAYPAL_CLIENT_ID", "")).strip()
    client_secret: str = (os.getenv("RESTOCKAI_PAYPAL_CLIENT_SECRET") or os.getenv("PAYPAL_CLIENT_SECRET", "")).strip()
    mode: str = os.getenv("PAYPAL_MODE", "sandbox").strip().lower()
    currency: str = os.getenv("PAYPAL_CURRENCY", "USD").strip().upper()
    allow_mock: bool = os.getenv("PAYPAL_ALLOW_MOCK", "false").strip().lower() in ("true", "1", "yes")

    @property
    def return_url(self) -> str:
        return _resolve_frontend_callback_url("PAYPAL_RETURN_URL", "/checkout/success")

    @property
    def cancel_url(self) -> str:
        return _resolve_frontend_callback_url("PAYPAL_CANCEL_URL", "/checkout/cancel")

    def validate_production_callbacks(self) -> None:
        _ = self.return_url
        _ = self.cancel_url

    @property
    def api_base(self) -> str:
        if self.mode == "live":
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

    @property
    def checkout_base(self) -> str:
        if self.mode == "live":
            return "https://www.paypal.com"
        return "https://www.sandbox.paypal.com"

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @property
    def is_mock(self) -> bool:
        # Strictly enabled only when credentials are missing AND allow_mock is explicitly True
        return (not self.is_configured) and self.allow_mock


paypal_settings = PayPalSettings()
