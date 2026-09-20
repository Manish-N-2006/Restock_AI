from fastapi import Request, HTTPException
from typing import Dict, Any
from .entities import build_user_entity

def get_current_principal(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency to extract the development identity from headers.
    Builds and returns a Cedar User entity.
    """
    user_id = request.headers.get("X-ReStockAI-User")
    
    if not user_id:
        # Default to a safe viewer or reject. We will reject if no identity is provided 
        # to ensure explicit identities in Phase 12 demo.
        # But to prevent breaking existing tests immediately, we can fallback to MANAGER if configured,
        # but the prompt said "Never silently default every request to MANAGER."
        raise HTTPException(status_code=403, detail="Missing X-ReStockAI-User header")
    
    # Simple deterministic mapping for development
    role = "VIEWER"
    store_scope = "*"
    
    if user_id.startswith("manager"):
        role = "MANAGER"
    elif user_id.startswith("operator"):
        role = "OPERATOR"
        # Example: operator-a -> STORE_A
        suffix = user_id.split("-")[-1]
        store_scope = f"STORE_{suffix.upper()}"
        
    return build_user_entity(user_id, role, store_scope)
