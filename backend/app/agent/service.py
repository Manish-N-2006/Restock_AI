from typing import Dict, Any, List
import json
from .agent import create_restock_agent

def ask_restock_agent(question: str) -> Dict[str, Any]:
    try:
        agent = create_restock_agent()
        result = agent(question)
        
        # Extract the tools used from the result (if available in metrics or state)
        # Note: Strands AgentResult might contain trace info, but for simplicity
        # we'll extract just the final text response.
        answer_text = "No response generated."
        if result and result.message:
            for content_block in result.message.content:
                if hasattr(content_block, 'text'):
                    answer_text = content_block.text
                    break

        return {
            "question": question,
            "answer": answer_text,
            "tools_used": [] # Extracting actual tool traces depends on detailed Strands trace inspection, omitted here for simplicity
        }
    except Exception as e:
        # Fallback for model unavailable
        return {
            "question": question,
            "answer": "The local ReStockAI agent is unavailable because the configured Ollama model cannot be reached or encountered an error.",
            "error_detail": str(e),
            "tools_used": []
        }

def analyze_inventory_with_agent(sku_id: str, store_id: str) -> Dict[str, Any]:
    question = f"What should I do with {sku_id} at {store_id}?"
    return ask_restock_agent(question)
