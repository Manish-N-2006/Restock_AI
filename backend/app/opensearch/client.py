import os
import logging
from opensearchpy import OpenSearch
from typing import Optional

logger = logging.getLogger(__name__)


def get_opensearch_client() -> Optional[OpenSearch]:
    """
    Create and return an OpenSearch client when configured.
    Returns None cleanly when disabled/unconfigured (or unset in production)
    so the SQL database fallback takes over without failing requests.
    """
    env = os.getenv("RESTOCKAI_ENV", "development").strip().lower()
    default_host = "" if env == "production" else "http://localhost:9200"
    host_url = os.getenv("RESTOCKAI_OPENSEARCH_HOST", default_host).strip()

    if not host_url:
        return None

    use_ssl = host_url.startswith("https://")
    verify_certs = os.getenv(
        "RESTOCKAI_OPENSEARCH_VERIFY_CERTS",
        "true" if use_ssl else "false",
    ).strip().lower() in ("true", "1", "yes")

    os_user = os.getenv("RESTOCKAI_OPENSEARCH_USER", "").strip()
    os_pass = os.getenv("RESTOCKAI_OPENSEARCH_PASSWORD", "").strip()

    client_kwargs = {
        "hosts": [host_url],
        "use_ssl": use_ssl,
        "verify_certs": verify_certs,
        "ssl_show_warn": False,
        "timeout": 2,
        "max_retries": 1,
    }
    if os_user and os_pass:
        client_kwargs["http_auth"] = (os_user, os_pass)

    try:
        # Defer network handshake until query time so FastAPI startup never blocks
        return OpenSearch(**client_kwargs)
    except Exception as exc:
        logger.warning("Failed to initialize OpenSearch client: %s", exc)
        return None
