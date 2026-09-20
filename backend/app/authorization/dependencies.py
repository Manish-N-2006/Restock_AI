from fastapi import Request, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import Callable, Optional, Dict, Any
from .actions import Action
from .engine import authorize
from .principal import get_current_principal
from .entities import build_generic_entity, build_transfer_entity, build_outcome_entity
from ..database import get_db
from ..services import transfer_engine, outcome_engine

import logging
logger = logging.getLogger(__name__)

def require_permission(action: Action, resource_type: str):
    """
    Creates a FastAPI dependency that enforces a Cedar policy check.
    It automatically fetches the necessary resource from the database if an ID is present in path_params.
    """
    def _dependency(
        request: Request,
        db: Session = Depends(get_db),
        principal: Dict[str, Any] = Depends(get_current_principal)
    ):
        resource_entity = build_generic_entity(resource_type)
        
        # Build specific resource entity if applicable
        if resource_type == "Transfer":
            transfer_id = request.path_params.get("transfer_id")
            if transfer_id:
                transfer = transfer_engine.get_transfer(db, transfer_id)
                if not transfer:
                    raise HTTPException(status_code=404, detail="Transfer not found")
                resource_entity = build_transfer_entity(
                    transfer_id=transfer.transfer_id,
                    source_store_id=transfer.source_store_id,
                    status=transfer.status
                )
        
        elif resource_type == "Outcome":
            # Just as an example if outcome_id is ever passed
            outcome_id = request.path_params.get("outcome_id")
            # For simplicity, if we don't have it, we just use a generic entity.
            # In Phase 12, outcomes mostly don't mutate except via finalizing
            pass
            
        result = authorize(
            principal_entity=principal,
            action=action.value,
            resource_entity=resource_entity
        )
        
        if not result.allowed:
            logger.warning(
                f"AUTHZ DENIED | User: {result.principal_id} | Role: {result.principal_role} | "
                f"Action: {result.action} | Resource: {result.resource_id} | Reason: {result.reason}"
            )
            raise HTTPException(status_code=403, detail="Forbidden: " + result.reason)
            
        return result
        
    return _dependency
