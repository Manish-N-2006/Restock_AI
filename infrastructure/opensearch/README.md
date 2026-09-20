# ReStockAI OpenSearch Historical Intelligence Layer

This directory contains the local Docker deployment configuration for OpenSearch.

OpenSearch is used by Phase 9 of ReStockAI as a **Historical Intelligence** layer. It stores denormalized representations of completed transfers and their finalized outcomes, allowing the Strands agent to search and answer historical questions.

## Usage

**Start OpenSearch (Local Development)**
```bash
docker compose -f infrastructure/opensearch/docker-compose.yml up -d
```

**Verify OpenSearch is running**
```bash
curl http://localhost:9200/
```

**Stop OpenSearch**
```bash
docker compose -f infrastructure/opensearch/docker-compose.yml down
```
*(Do not include `-v` unless you want to destroy the local search index data).*

## Security Notice

> [!WARNING]  
> Security is intentionally disabled (`plugins.security.disabled=true`) **only** for this local development container to simplify setup and testing. This container should **not** be exposed publicly or used in production.

## Database Consistency Model

OpenSearch acts as a secondary derived index. **SQLite remains the authoritative transactional source of truth.** 
Inventory levels, reservations, transfer state machines, and outcome finalizations are controlled exclusively by SQLite. If OpenSearch goes down, the core ReStockAI business engines will continue operating gracefully without disruption.
