import os
import cedarpy
from pydantic import BaseModel
from typing import List, Optional

# Paths to Cedar files
CEDAR_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "infrastructure", "cedar")
SCHEMA_PATH = os.path.join(CEDAR_DIR, "schema.cedarschema")
POLICIES_PATH = os.path.join(CEDAR_DIR, "policies.cedar")

# Cache to avoid reloading from disk on every request
_schema_cache = None
_policies_cache = None

class AuthorizationResult(BaseModel):
    allowed: bool
    principal_id: str
    principal_role: str
    action: str
    resource_type: str
    resource_id: str
    reason: str
    
def _load_cedar_files():
    global _schema_cache, _policies_cache
    if _schema_cache is None:
        with open(SCHEMA_PATH, "r") as f:
            _schema_cache = f.read()
    if _policies_cache is None:
        with open(POLICIES_PATH, "r") as f:
            _policies_cache = f.read()
    return _schema_cache, _policies_cache

def authorize(
    principal_entity: dict,
    action: str,
    resource_entity: dict,
    context: Optional[dict] = None
) -> AuthorizationResult:
    """
    Evaluates whether the principal is allowed to perform the action on the resource.
    """
    schema, policies = _load_cedar_files()
    
    principal_uid = principal_entity["uid"]
    resource_uid = resource_entity["uid"]
    
    request = {
        "principal": f'{principal_uid["type"]}::"{principal_uid["id"]}"',
        "action": f'ReStockAI::Action::"{action}"',
        "resource": f'{resource_uid["type"]}::"{resource_uid["id"]}"',
        "context": context or {}
    }
    
    entities = [principal_entity, resource_entity]
    
    try:
        authz_result: cedarpy.AuthzResult = cedarpy.is_authorized(
            request=request,
            policies=policies,
            entities=entities,
            schema=schema
        )
        
        allowed = authz_result.decision == cedarpy.Decision.Allow
        
        reason = "Allowed by policy." if allowed else "Denied by policy."
        if authz_result.diagnostics.errors:
            reason = f"Errors: {authz_result.diagnostics.errors}"
            
        return AuthorizationResult(
            allowed=allowed,
            principal_id=principal_uid["id"],
            principal_role=principal_entity["attrs"].get("role", "UNKNOWN"),
            action=action,
            resource_type=resource_uid["type"],
            resource_id=resource_uid["id"],
            reason=reason
        )
    except Exception as e:
        return AuthorizationResult(
            allowed=False,
            principal_id=principal_uid["id"],
            principal_role=principal_entity["attrs"].get("role", "UNKNOWN"),
            action=action,
            resource_type=resource_uid["type"],
            resource_id=resource_uid["id"],
            reason=f"Authorization Engine Error: {str(e)}"
        )
