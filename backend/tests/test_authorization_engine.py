import pytest
from app.authorization.engine import authorize
from app.authorization.entities import build_user_entity, build_generic_entity, build_transfer_entity, build_outcome_entity
from app.authorization.actions import Action

def test_manager_permissions():
    principal = build_user_entity("manager-1", "MANAGER", "*")
    resource = build_generic_entity("Inventory")
    
    # Manager can do anything
    result = authorize(principal, Action.VIEW_INVENTORY.value, resource)
    assert result.allowed is True
    
    transfer_resource = build_generic_entity("Transfer")
    result = authorize(principal, Action.CREATE_TRANSFER.value, transfer_resource)
    assert result.allowed is True

def test_viewer_permissions():
    principal = build_user_entity("viewer-1", "VIEWER", "*")
    resource = build_generic_entity("Inventory")
    
    # Viewer can read
    result = authorize(principal, Action.VIEW_INVENTORY.value, resource)
    assert result.allowed is True
    
    # Viewer cannot mutate
    result = authorize(principal, Action.CREATE_TRANSFER.value, resource)
    assert result.allowed is False

def test_operator_store_scope():
    principal = build_user_entity("operator-1", "OPERATOR", "STORE_A")
    
    # Scoped transfer
    transfer_in_scope = build_transfer_entity("tr-1", "STORE_A", "PENDING")
    transfer_out_of_scope = build_transfer_entity("tr-2", "STORE_B", "PENDING")
    
    result = authorize(principal, Action.COMPLETE_TRANSFER.value, transfer_in_scope)
    assert result.allowed is True
    
    result = authorize(principal, Action.COMPLETE_TRANSFER.value, transfer_out_of_scope)
    assert result.allowed is False

def test_explicit_denies():
    principal = build_user_entity("manager-1", "MANAGER", "*")
    
    # Cannot modify finalized outcome even as Manager
    finalized_outcome = build_outcome_entity("out-1", True)
    result = authorize(principal, Action.MODIFY_FINALIZED_OUTCOME.value, finalized_outcome)
    assert result.allowed is False
    
    # Cannot complete already completed transfer
    completed_transfer = build_transfer_entity("tr-1", "STORE_A", "COMPLETED")
    result = authorize(principal, Action.COMPLETE_TRANSFER.value, completed_transfer)
    assert result.allowed is False
