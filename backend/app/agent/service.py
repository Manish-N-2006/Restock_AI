import os
from typing import Dict, Any, List
import json
from .agent import create_restock_agent

def ask_restock_agent(question: str) -> Dict[str, Any]:
    try:
        agent = create_restock_agent()
        result = agent(question)
        
        answer_text = "No response generated."
        if result and hasattr(result, "message") and result.message:
            msg = result.message
            content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else [])
            for block in content:
                if isinstance(block, dict):
                    if "text" in block and block["text"]:
                        answer_text = block["text"]
                        break
                elif hasattr(block, "text") and block.text:
                    answer_text = block.text
                    break
            if answer_text == "No response generated." and hasattr(result, "text"):
                answer_text = str(result.text)

        return {
            "question": question,
            "answer": answer_text,
            "tools_used": []
        }
    except Exception as e:
        provider = os.getenv("RESTOCKAI_LLM_PROVIDER", "groq").lower()
        if provider == "ollama" or "ollama" in str(e).lower():
            msg = "The local ReStockAI agent is unavailable because the configured Ollama model cannot be reached or encountered an error."
        else:
            msg = f"The ReStockAI agent ({provider.upper()}) encountered an error: {str(e)}"
        return {
            "question": question,
            "answer": msg,
            "error_detail": str(e),
            "tools_used": []
        }

def analyze_inventory_with_agent(sku_id: str, store_id: str) -> Dict[str, Any]:
    question = f"What should I do with {sku_id} at {store_id}?"
    return ask_restock_agent(question)
