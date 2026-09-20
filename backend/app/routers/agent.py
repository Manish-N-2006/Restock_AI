import os
import requests
from fastapi import APIRouter
from typing import Dict, Any

from ..schemas.agent import AskRequest, AskResponse, HealthResponse
from ..agent import ask_restock_agent, analyze_inventory_with_agent

router = APIRouter(prefix="/api/agent", tags=["Agent"])

@router.post("/ask", response_model=AskResponse)
def api_agent_ask(req: AskRequest):
    """Ask the ReStockAI Manager Assistant a question."""
    result = ask_restock_agent(req.question)
    return AskResponse(
        question=result["question"],
        answer=result["answer"],
        tools_used=result["tools_used"]
    )

@router.get("/analyze/{sku_id}", response_model=AskResponse)
def api_agent_analyze(sku_id: str, store_id: str):
    """Generate a guided ReStockAI analysis for an item."""
    result = analyze_inventory_with_agent(sku_id, store_id)
    return AskResponse(
        question=result["question"],
        answer=result["answer"],
        tools_used=result["tools_used"]
    )

@router.get("/health", response_model=HealthResponse)
def api_agent_health():
    """Check the health of the local Ollama provider."""
    host = os.getenv("RESTOCKAI_OLLAMA_HOST", "http://localhost:11434")
    model_name = os.getenv("RESTOCKAI_AGENT_MODEL", "llama3.1")
    
    available = False
    try:
        # Check if Ollama is running
        res = requests.get(f"{host}/api/tags", timeout=2)
        if res.status_code == 200:
            models = res.json().get("models", [])
            # For simplicity, if Ollama is up, we say available. 
            # We could check if model_name is in models.
            available = any(m.get("name", "").startswith(model_name) for m in models)
            # If the user didn't pull the exact model but Ollama is up, we might fail later,
            # but we can just say available if the service is up for now, or check strictly.
    except Exception:
        pass

    return HealthResponse(
        configured=True,
        available=available,
        model_provider="ollama",
        ollama_host=host,
        model_name=model_name
    )
