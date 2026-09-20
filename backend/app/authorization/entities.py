def build_user_entity(user_id: str, role: str, store_scope: str) -> dict:
    """Builds a Cedar User entity"""
    return {
        "uid": {
            "type": "ReStockAI::User",
            "id": user_id
        },
        "attrs": {
            "role": role,
            "store_scope": store_scope
        },
        "parents": []
    }

def build_transfer_entity(transfer_id: str, source_store_id: str, status: str) -> dict:
    """Builds a Cedar Transfer entity"""
    return {
        "uid": {
            "type": "ReStockAI::Transfer",
            "id": transfer_id
        },
        "attrs": {
            "source_store_id": source_store_id,
            "status": status
        },
        "parents": []
    }

def build_outcome_entity(outcome_id: str, finalized: bool) -> dict:
    """Builds a Cedar Outcome entity"""
    return {
        "uid": {
            "type": "ReStockAI::Outcome",
            "id": outcome_id
        },
        "attrs": {
            "finalized": finalized
        },
        "parents": []
    }

def build_generic_entity(entity_type: str, entity_id: str = "GLOBAL") -> dict:
    """Builds a generic entity with no attributes (e.g. for Risk, Inventory, History)"""
    attrs = {}
    if entity_type == "Transfer":
        attrs = {"source_store_id": "*", "status": "PENDING"}
    elif entity_type == "Outcome":
        attrs = {"finalized": False}
        
    return {
        "uid": {
            "type": f"ReStockAI::{entity_type}",
            "id": entity_id
        },
        "attrs": attrs,
        "parents": []
    }
