import json
import logging
from typing import Dict, Any

from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.database import SessionLocal
from backend.app.models.inventory import Inventory
from backend.app.services.risk_engine import calculate_inventory_risk
from backend.app.services.demand_engine import find_destination_candidates
from backend.app.services.decision_engine import evaluate_decision
from backend.app.services.logistics_engine import get_integrated_recommendation

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def _build_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS SAM Local Lambda handler for ReStockAI Inventory Recovery Analysis.
    """
    logger.info("Received event: %s", json.dumps(event))
    
    # Extract payload from API Gateway event format, or direct invoke format
    try:
        body = event
        if "body" in event:
            body_content = event["body"]
            if isinstance(body_content, str):
                body = json.loads(body_content)
            else:
                body = body_content
                
        sku_id = body.get("sku_id")
        source_store_id = body.get("source_store_id")
        
        if not sku_id or not source_store_id:
            return _build_response(400, {"error": "Missing sku_id or source_store_id"})
            
    except json.JSONDecodeError:
        return _build_response(400, {"error": "Invalid JSON in request body"})
        
    with SessionLocal() as db:
        try:
            # 1. Verify Inventory
            inv = db.query(Inventory).filter(
                Inventory.sku_id == sku_id, 
                Inventory.store_id == source_store_id
            ).first()
            
            if not inv:
                return _build_response(404, {"error": f"No inventory found for SKU {sku_id} at {source_store_id}"})
                
            # 2. Risk Engine
            risk = calculate_inventory_risk(inv)
            
            # 3. Demand Engine
            demand_match = find_destination_candidates(db, sku_id, source_store_id)
            
            # 4. Decision Engine
            decision = evaluate_decision(db, sku_id, source_store_id)
            
            # 5. Logistics Engine (if action is TRANSFER)
            logistics = None
            execution_ready = False
            
            if decision.selected_action.value == "TRANSFER":
                recommendation = get_integrated_recommendation(db, sku_id, source_store_id)
                if recommendation.logistics:
                    logistics = recommendation.logistics.model_dump()
                    execution_ready = True
                    
            response_payload = {
                "sku_id": sku_id,
                "source_store_id": source_store_id,
                "risk": risk.model_dump(),
                "demand": demand_match.model_dump(),
                "decision": decision.model_dump(),
                "logistics": logistics,
                "execution_ready": execution_ready
            }
            
            return _build_response(200, response_payload)
            
        except HTTPException as he:
            logger.error("HTTPException in services: %s", he.detail)
            return _build_response(he.status_code, {"error": he.detail})
        except ValidationError as ve:
            logger.error("Pydantic Validation Error: %s", str(ve))
            return _build_response(500, {"error": "Internal validation error", "details": ve.errors()})
        except Exception as e:
            logger.exception("Unexpected error")
            return _build_response(500, {"error": "Internal server error"})
