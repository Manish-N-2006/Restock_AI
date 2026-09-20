import os
import logging
from opensearchpy import OpenSearch
from typing import Optional

logger = logging.getLogger(__name__)

def get_opensearch_client() -> Optional[OpenSearch]:
    """
    Creates and returns an OpenSearch client.
    Fails gracefully by returning None if the host is not configured properly or is unreachable.
    """
    host_url = os.getenv("RESTOCKAI_OPENSEARCH_HOST", "http://localhost:9200")
    
    try:
        client = OpenSearch(
            hosts=[host_url],
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False
        )
        
        # We don't perform a ping here to prevent blocking FastAPI startup if OS is down.
        # Health checks are done explicitly via the health endpoint or during indexing.
        return client
    except Exception as e:
        logger.warning(f"Failed to initialize OpenSearch client: {str(e)}")
        return None
