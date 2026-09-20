import os
import logging
from opensearchpy import OpenSearch
from .client import get_opensearch_client

logger = logging.getLogger(__name__)

INDEX_NAME = os.getenv("RESTOCKAI_OPENSEARCH_INDEX", "restockai-history")

INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0
    },
    "mappings": {
        "properties": {
            "document_id": {"type": "keyword"},
            "document_type": {"type": "keyword"},
            "transfer_id": {"type": "keyword"},
            "sku_id": {"type": "keyword"},
            "product_name": {"type": "text"},
            "source_store_id": {"type": "keyword"},
            "destination_store_id": {"type": "keyword"},
            "quantity": {"type": "integer"},
            
            "decision": {
                "properties": {
                    "action": {"type": "keyword"},
                    "expected_net_recovery": {"type": "float"}
                }
            },
            
            "logistics": {
                "properties": {
                    "partner_id": {"type": "keyword"},
                    "partner_name": {"type": "keyword"},
                    "estimated_cost": {"type": "float"},
                    "estimated_eta_minutes": {"type": "integer"}
                }
            },
            
            "outcome": {
                "properties": {
                    "outcome_status": {"type": "keyword"},
                    "predicted_units_sold": {"type": "integer"},
                    "actual_units_sold": {"type": "integer"},
                    "actual_recovered_value": {"type": "float"},
                    "actual_logistics_cost": {"type": "float"},
                    "actual_handling_cost": {"type": "float"},
                    "actual_net_recovery": {"type": "float"},
                    "recovery_variance": {"type": "float"},
                    "sell_through_rate": {"type": "float"},
                    "recovery_accuracy_percentage": {"type": "float"}
                }
            },
            
            "created_at": {"type": "date"},
            "completed_at": {"type": "date"},
            "outcome_finalized_at": {"type": "date"},
            "explanation": {"type": "text"}
        }
    }
}

def index_exists(client: OpenSearch) -> bool:
    return client.indices.exists(index=INDEX_NAME)

def create_history_index(client: OpenSearch):
    if not index_exists(client):
        try:
            client.indices.create(index=INDEX_NAME, body=INDEX_MAPPING)
            logger.info(f"Created OpenSearch index: {INDEX_NAME}")
        except Exception as e:
            logger.error(f"Failed to create index {INDEX_NAME}: {str(e)}")
    else:
        logger.info(f"Index {INDEX_NAME} already exists.")

def delete_history_index(client: OpenSearch):
    if index_exists(client):
        try:
            client.indices.delete(index=INDEX_NAME)
            logger.info(f"Deleted OpenSearch index: {INDEX_NAME}")
        except Exception as e:
            logger.error(f"Failed to delete index {INDEX_NAME}: {str(e)}")

def recreate_history_index(client: OpenSearch):
    delete_history_index(client)
    create_history_index(client)

def get_index_mapping(client: OpenSearch):
    return client.indices.get_mapping(index=INDEX_NAME)

def setup_opensearch():
    """Initializes the OpenSearch index if the service is available."""
    client = get_opensearch_client()
    if client:
        try:
            create_history_index(client)
        except Exception as e:
            logger.warning(f"Could not setup OpenSearch index: {str(e)}")
