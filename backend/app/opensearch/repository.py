import logging
from typing import Dict, Any, List, Optional
from opensearchpy import OpenSearch
from .client import get_opensearch_client
from .index_manager import INDEX_NAME
from .serializers import serialize_transfer_to_document, serialize_outcome_to_document
from ..models.transfer import TransferOrder
from ..models.outcome import Outcome

logger = logging.getLogger(__name__)

def index_transfer_history(transfer: TransferOrder):
    """
    Indexes a completed transfer into OpenSearch.
    Idempotent operation (upsert). Does not throw if OS is unavailable.
    """
    client = get_opensearch_client()
    if not client:
        return
        
    doc = serialize_transfer_to_document(transfer)
    try:
        client.index(index=INDEX_NAME, id=doc["document_id"], body=doc)
        logger.info(f"Successfully indexed transfer history: {transfer.transfer_id}")
    except Exception as e:
        logger.error(f"Failed to index transfer history for {transfer.transfer_id}: {str(e)}")

def upsert_outcome_history(outcome: Outcome, transfer: Optional[TransferOrder] = None) -> bool:
    """
    Updates the historical document with final outcome metrics.
    Returns True if successful, False if it failed or OS is unavailable.
    """
    client = get_opensearch_client()
    if not client:
        return False
        
    doc = serialize_outcome_to_document(outcome, transfer)
    try:
        # Use update API with doc_as_upsert to create if it doesn't exist
        client.update(
            index=INDEX_NAME, 
            id=doc["document_id"], 
            body={"doc": doc, "doc_as_upsert": True}
        )
        logger.info(f"Successfully upserted outcome history for: {outcome.transfer_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to upsert outcome history for {outcome.transfer_id}: {str(e)}")
        return False

def get_history_by_transfer_id(transfer_id: str) -> Optional[Dict[str, Any]]:
    client = get_opensearch_client()
    if not client:
        return None
        
    try:
        res = client.get(index=INDEX_NAME, id=transfer_id)
        return res["_source"]
    except Exception as e:
        logger.warning(f"History document not found for {transfer_id}: {str(e)}")
        return None

def search_history(
    q: Optional[str] = None,
    sku_id: Optional[str] = None,
    source_store_id: Optional[str] = None,
    destination_store_id: Optional[str] = None,
    action: Optional[str] = None,
    partner_id: Optional[str] = None,
    outcome_status: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    client = get_opensearch_client()
    if not client:
        # Graceful Fallback to SQLite
        from ..database import SessionLocal
        from ..models.transfer import TransferOrder
        from ..models.outcome import Outcome
        
        with SessionLocal() as db:
            from sqlalchemy import or_
            query = db.query(TransferOrder).join(Outcome, TransferOrder.transfer_id == Outcome.transfer_id)
            
            if q:
                search_term = f"%{q}%"
                query = query.filter(
                    or_(
                        TransferOrder.sku_id.ilike(search_term),
                        TransferOrder.product_name.ilike(search_term),
                        TransferOrder.source_store_id.ilike(search_term),
                        TransferOrder.destination_store_id.ilike(search_term)
                    )
                )
                
            if sku_id:
                query = query.filter(TransferOrder.sku_id == sku_id)
            if source_store_id:
                query = query.filter(TransferOrder.source_store_id == source_store_id)
            if destination_store_id:
                query = query.filter(TransferOrder.destination_store_id == destination_store_id)
            if outcome_status:
                query = query.filter(Outcome.outcome_status == outcome_status)
                
            results = query.order_by(TransferOrder.created_at.desc()).limit(limit).all()
            
            mapped_results = []
            for t in results:
                o = db.query(Outcome).filter(Outcome.transfer_id == t.transfer_id).first()
                mapped_results.append({
                    "transfer_id": t.transfer_id,
                    "sku_id": t.sku_id,
                    "source_store_id": t.source_store_id,
                    "destination_store_id": t.destination_store_id,
                    "decision": {"action": "TRANSFER"},
                    "outcome": {
                        "actual_net_recovery": o.actual_net_recovery if o else 0,
                        "recovery_accuracy_percentage": o.recovery_accuracy_percentage if o else 0,
                        "actual_units_sold": o.actual_units_sold if o else 0,
                        "outcome_status": o.outcome_status.value if o else "PENDING"
                    }
                })
                
            return {"total": len(mapped_results), "results": mapped_results}
        
    must_clauses = []
    
    if q:
        must_clauses.append({"multi_match": {"query": q, "fields": ["product_name", "explanation"]}})
    if sku_id:
        must_clauses.append({"term": {"sku_id": sku_id}})
    if source_store_id:
        must_clauses.append({"term": {"source_store_id": source_store_id}})
    if destination_store_id:
        must_clauses.append({"term": {"destination_store_id": destination_store_id}})
    if action:
        must_clauses.append({"term": {"decision.action": action}})
    if partner_id:
        must_clauses.append({"term": {"logistics.partner_id": partner_id}})
    if outcome_status:
        must_clauses.append({"term": {"outcome.outcome_status": outcome_status}})
        
    query = {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}
    
    try:
        res = client.search(
            index=INDEX_NAME,
            body={
                "query": query,
                "size": limit,
                "sort": [{"created_at": {"order": "desc", "unmapped_type": "date"}}]
            }
        )
        hits = res["hits"]["hits"]
        total = res["hits"]["total"]["value"]
        
        results = [hit["_source"] for hit in hits]
        return {"total": total, "results": results}
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        return {"total": 0, "results": [], "error": str(e)}

def search_similar_scenarios(
    sku_id: Optional[str] = None,
    source_store_id: Optional[str] = None,
    product_name: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 5
) -> Dict[str, Any]:
    # For Phase 9, similar scenario search is structured filtering
    # In future phases, this could be upgraded to vector/semantic search
    return search_history(
        q=product_name,
        sku_id=sku_id,
        source_store_id=source_store_id,
        action=action,
        limit=limit
    )

def get_history_summary() -> Dict[str, Any]:
    client = get_opensearch_client()
    if not client:
        # Graceful Fallback to SQLite
        from ..database import SessionLocal
        from ..models.transfer import TransferOrder
        from ..models.outcome import Outcome
        from sqlalchemy import func
        
        with SessionLocal() as db:
            total_indexed = db.query(TransferOrder).filter(TransferOrder.status == "COMPLETED").count()
            total_finalized = db.query(Outcome).filter(Outcome.outcome_status == "FINALIZED").count()
            total_units = db.query(func.sum(TransferOrder.quantity)).filter(TransferOrder.status == "COMPLETED").scalar() or 0
            
            # Outcome sums
            net_recovery = db.query(func.sum(Outcome.actual_net_recovery)).filter(Outcome.outcome_status == "FINALIZED").scalar() or 0
            avg_accuracy = db.query(func.avg(Outcome.recovery_accuracy_percentage)).filter(Outcome.outcome_status == "FINALIZED").scalar()
            avg_sell = db.query(func.avg(Outcome.sell_through_rate)).filter(Outcome.outcome_status == "FINALIZED").scalar()
            
            return {
                "total_indexed_transfers": total_indexed,
                "total_finalized_outcomes": total_finalized,
                "total_units_moved": total_units,
                "total_actual_net_recovery": net_recovery,
                "average_recovery_accuracy": avg_accuracy,
                "average_sell_through_rate": avg_sell,
                "transfer_count_by_action": {"TRANSFER": total_indexed},
                "transfer_count_by_partner": {"SQLite Fallback": total_indexed}
            }
        
    try:
        res = client.search(
            index=INDEX_NAME,
            body={
                "size": 0,
                "aggs": {
                    "total_completed": {"value_count": {"field": "transfer_id"}},
                    "total_finalized": {"filter": {"term": {"outcome.outcome_status": "FINALIZED"}}},
                    "total_units": {"sum": {"field": "quantity"}},
                    "total_net_recovery": {"sum": {"field": "outcome.actual_net_recovery"}},
                    "avg_accuracy": {"avg": {"field": "outcome.recovery_accuracy_percentage"}},
                    "avg_sell_through": {"avg": {"field": "outcome.sell_through_rate"}},
                    "by_action": {
                        "terms": {"field": "decision.action"}
                    },
                    "by_partner": {
                        "terms": {"field": "logistics.partner_name"}
                    }
                }
            }
        )
        
        aggs = res.get("aggregations", {})
        
        return {
            "total_indexed_transfers": aggs.get("total_completed", {}).get("value", 0),
            "total_finalized_outcomes": aggs.get("total_finalized", {}).get("doc_count", 0),
            "total_units_moved": aggs.get("total_units", {}).get("value", 0),
            "total_actual_net_recovery": aggs.get("total_net_recovery", {}).get("value", 0),
            "average_recovery_accuracy": aggs.get("avg_accuracy", {}).get("value", None),
            "average_sell_through_rate": aggs.get("avg_sell_through", {}).get("value", None),
            "transfer_count_by_action": {b["key"]: b["doc_count"] for b in aggs.get("by_action", {}).get("buckets", [])},
            "transfer_count_by_partner": {b["key"]: b["doc_count"] for b in aggs.get("by_partner", {}).get("buckets", [])}
        }
    except Exception as e:
        logger.error(f"Summary aggregation failed: {str(e)}")
        return {"error": str(e)}

def delete_history_document(transfer_id: str):
    client = get_opensearch_client()
    if not client:
        return
        
    try:
        client.delete(index=INDEX_NAME, id=transfer_id)
    except Exception as e:
        logger.warning(f"Failed to delete history document {transfer_id}: {str(e)}")
