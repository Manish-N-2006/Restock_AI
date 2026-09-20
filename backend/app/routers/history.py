from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from ..schemas.history import HistorySearchResponse, HistorySearchResult, HistorySummaryResponse, OpenSearchHealthResponse
from ..opensearch.repository import search_history, get_history_by_transfer_id, search_similar_scenarios, get_history_summary
from ..opensearch.client import get_opensearch_client
from ..opensearch.index_manager import INDEX_NAME
import os
from ..authorization.dependencies import require_permission
from ..authorization.actions import Action
from fastapi import Depends

router = APIRouter(prefix="/api/history", tags=["history"])

@router.get("/health", response_model=OpenSearchHealthResponse, dependencies=[Depends(require_permission(Action.VIEW_HISTORY, "History"))])
def get_health():
    client = get_opensearch_client()
    configured = bool(os.getenv("RESTOCKAI_OPENSEARCH_HOST", "http://localhost:9200"))
    
    available = False
    if client:
        try:
            available = client.ping()
        except:
            pass
            
    return OpenSearchHealthResponse(
        configured=configured,
        available=available,
        index=INDEX_NAME
    )

@router.get("/search", response_model=HistorySearchResponse, dependencies=[Depends(require_permission(Action.VIEW_HISTORY, "History"))])
def search(
    q: Optional[str] = None,
    sku_id: Optional[str] = None,
    source_store_id: Optional[str] = None,
    destination_store_id: Optional[str] = None,
    action: Optional[str] = None,
    partner_id: Optional[str] = None,
    outcome_status: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100)
):
    res = search_history(
        q=q,
        sku_id=sku_id,
        source_store_id=source_store_id,
        destination_store_id=destination_store_id,
        action=action,
        partner_id=partner_id,
        outcome_status=outcome_status,
        limit=limit
    )
    
    if "error" in res and res["error"] == "OpenSearch is unavailable":
        raise HTTPException(status_code=503, detail="OpenSearch historical indexing is unavailable.")
        
    mapped_results = []
    for hit in res.get("results", []):
        outcome = hit.get("outcome", {})
        decision = hit.get("decision", {})
        mapped_results.append(HistorySearchResult(
            transfer_id=hit.get("transfer_id", ""),
            sku_id=hit.get("sku_id", ""),
            source_store_id=hit.get("source_store_id", ""),
            destination_store_id=hit.get("destination_store_id"),
            action=decision.get("action"),
            actual_net_recovery=outcome.get("actual_net_recovery"),
            recovery_accuracy_percentage=outcome.get("recovery_accuracy_percentage"),
            actual_units_sold=outcome.get("actual_units_sold")
        ))
        
    return HistorySearchResponse(
        total=res.get("total", 0),
        results=mapped_results
    )

@router.get("/transfer/{transfer_id}", dependencies=[Depends(require_permission(Action.VIEW_HISTORY, "History"))])
def get_transfer_history(transfer_id: str):
    doc = get_history_by_transfer_id(transfer_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Historical document not found for this transfer.")
    return doc

@router.get("/similar", response_model=HistorySearchResponse, dependencies=[Depends(require_permission(Action.VIEW_HISTORY, "History"))])
def get_similar(
    sku_id: Optional[str] = None,
    source_store_id: Optional[str] = None,
    product_name: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(5, ge=1, le=50)
):
    res = search_similar_scenarios(
        sku_id=sku_id,
        source_store_id=source_store_id,
        product_name=product_name,
        action=action,
        limit=limit
    )
    
    if "error" in res and res["error"] == "OpenSearch is unavailable":
        raise HTTPException(status_code=503, detail="OpenSearch historical indexing is unavailable.")
        
    mapped_results = []
    for hit in res.get("results", []):
        outcome = hit.get("outcome", {})
        decision = hit.get("decision", {})
        mapped_results.append(HistorySearchResult(
            transfer_id=hit.get("transfer_id", ""),
            sku_id=hit.get("sku_id", ""),
            source_store_id=hit.get("source_store_id", ""),
            destination_store_id=hit.get("destination_store_id"),
            action=decision.get("action"),
            actual_net_recovery=outcome.get("actual_net_recovery"),
            recovery_accuracy_percentage=outcome.get("recovery_accuracy_percentage"),
            actual_units_sold=outcome.get("actual_units_sold")
        ))
        
    return HistorySearchResponse(
        total=res.get("total", 0),
        results=mapped_results
    )

@router.get("/summary", response_model=HistorySummaryResponse, dependencies=[Depends(require_permission(Action.VIEW_HISTORY, "History"))])
def get_summary():
    res = get_history_summary()
    if "error" in res:
        raise HTTPException(status_code=503, detail="OpenSearch historical indexing is unavailable.")
        
    return HistorySummaryResponse(
        total_indexed_transfers=res.get("total_indexed_transfers", 0),
        total_finalized_outcomes=res.get("total_finalized_outcomes", 0),
        total_units_moved=res.get("total_units_moved", 0),
        total_actual_net_recovery=res.get("total_actual_net_recovery", 0.0),
        average_recovery_accuracy=res.get("average_recovery_accuracy"),
        average_sell_through_rate=res.get("average_sell_through_rate"),
        transfer_count_by_action=res.get("transfer_count_by_action", {}),
        transfer_count_by_partner=res.get("transfer_count_by_partner", {})
    )

@router.get("/store/{store_id}", response_model=Dict[str, Any], dependencies=[Depends(require_permission(Action.VIEW_HISTORY, "History"))])
def get_store_history(store_id: str):
    client = get_opensearch_client()
    if not client:
        raise HTTPException(status_code=503, detail="OpenSearch is unavailable")
        
    try:
        res = client.search(
            index=INDEX_NAME,
            body={
                "size": 0,
                "aggs": {
                    "inbound": {
                        "filter": {"term": {"destination_store_id": store_id}},
                        "aggs": {
                            "units": {"sum": {"field": "quantity"}},
                            "recovery": {"sum": {"field": "outcome.actual_recovered_value"}},
                            "avg_accuracy": {"avg": {"field": "outcome.recovery_accuracy_percentage"}}
                        }
                    },
                    "outbound": {
                        "filter": {"term": {"source_store_id": store_id}},
                        "aggs": {
                            "units": {"sum": {"field": "quantity"}},
                            "recovery": {"sum": {"field": "outcome.actual_recovered_value"}}
                        }
                    }
                }
            }
        )
        aggs = res.get("aggregations", {})
        inbound = aggs.get("inbound", {})
        outbound = aggs.get("outbound", {})
        
        return {
            "store_id": store_id,
            "inbound_transfers": inbound.get("doc_count", 0),
            "outbound_transfers": outbound.get("doc_count", 0),
            "total_units_received": inbound.get("units", {}).get("value", 0),
            "total_units_sent": outbound.get("units", {}).get("value", 0),
            "actual_recovered_value_inbound": inbound.get("recovery", {}).get("value", 0.0),
            "actual_recovered_value_outbound": outbound.get("recovery", {}).get("value", 0.0),
            "average_outcome_accuracy_inbound": inbound.get("avg_accuracy", {}).get("value", None)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
