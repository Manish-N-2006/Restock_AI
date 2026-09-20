import logging
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.transfer import TransferOrder, TransferStatus
from ..models.outcome import Outcome, OutcomeStatus
from .index_manager import setup_opensearch
from .repository import index_transfer_history, upsert_outcome_history
from .client import get_opensearch_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backfill():
    client = get_opensearch_client()
    if not client:
        logger.error("Cannot backfill: OpenSearch is unavailable.")
        return
        
    logger.info("Ensuring OpenSearch index exists...")
    setup_opensearch()
    
    with SessionLocal() as db:
        logger.info("Fetching completed transfers from SQLite...")
        completed_transfers = db.query(TransferOrder).filter(TransferOrder.status == TransferStatus.COMPLETED).all()
        logger.info(f"Found {len(completed_transfers)} completed transfers.")
        
        for t in completed_transfers:
            logger.info(f"Indexing transfer {t.transfer_id}...")
            index_transfer_history(t)
            
        logger.info("Fetching finalized outcomes from SQLite...")
        finalized_outcomes = db.query(Outcome).filter(Outcome.outcome_status == OutcomeStatus.FINALIZED).all()
        logger.info(f"Found {len(finalized_outcomes)} finalized outcomes.")
        
        for o in finalized_outcomes:
            logger.info(f"Upserting outcome {o.outcome_id} for transfer {o.transfer_id}...")
            transfer = db.query(TransferOrder).filter(TransferOrder.transfer_id == o.transfer_id).first()
            upsert_outcome_history(o, transfer)
            
        logger.info("Backfill complete.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Backfill OpenSearch indices")
    parser.add_argument("--reset", action="store_true", help="Delete the index before backfilling")
    args = parser.parse_args()

    if args.reset:
        from .index_manager import INDEX_NAME
        client = get_opensearch_client()
        if client and client.indices.exists(index=INDEX_NAME):
            client.indices.delete(index=INDEX_NAME)
            logger.info(f"Deleted OpenSearch index {INDEX_NAME}.")

    backfill()
