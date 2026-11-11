from typing import Any, Dict
from fastapi import Depends
from .entities import build_user_entity
from ..auth.service import require_authenticated_session


def get_current_principal(
    claims: Dict[str, Any] = Depends(require_authenticated_session),
) -> Dict[str, Any]:
    """
    Resolve the Cedar principal strictly from the server-verified session cookie.
    Never trusts client-supplied identity headers such as X-ReStockAI-User.
    """
    return build_user_entity(
        user_id=claims["sub"],
        role=claims["role"],
        store_scope=claims.get("store_scope", "*"),
    )
