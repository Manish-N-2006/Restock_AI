from fastapi import APIRouter, Depends
from typing import Dict, Any
from pydantic import BaseModel
from ..authorization.engine import authorize, AuthorizationResult
from ..authorization.principal import get_current_principal
from ..authorization.entities import build_generic_entity, build_transfer_entity, build_outcome_entity

router = APIRouter()

class AuthorizationCheckRequest(BaseModel):
    action: str
    resource_type: str
    resource_id: str

@router.post("/check", response_model=AuthorizationResult)
def check_authorization(
    request: AuthorizationCheckRequest,
    principal: Dict[str, Any] = Depends(get_current_principal)
):
    """
    Check if the current principal is allowed to perform the given action on the given resource.
    For demonstration and debugging purposes.
    """
    # For generic checks, we just build a generic entity with the given ID
    # In a real check, we'd fetch the DB object to get attributes if needed
    resource_entity = build_generic_entity(request.resource_type, request.resource_id)
    
    # Mocking attributes if it's a specific type for demo scenarios
    if request.resource_type == "Transfer":
        # Usually we would query DB. Here we mock a basic one for the pure check endpoint
        # The true enforcement dependency actually fetches the DB object.
        resource_entity["attrs"]["source_store_id"] = "STORE_A"
        resource_entity["attrs"]["status"] = "PENDING"
        
    elif request.resource_type == "Outcome":
        resource_entity["attrs"]["finalized"] = False

    return authorize(
        principal_entity=principal,
        action=request.action,
        resource_entity=resource_entity
    )
