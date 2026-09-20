from typing import Dict, Any, List
import json
import re
from .agent import create_restock_agent, get_configured_model_name, model_supports_tools
from .prompts import SYSTEM_PROMPT
from .tools import (
    get_inventory_risk,
    find_destination_matches,
    evaluate_recovery_options,
    optimize_logistics,
    get_transfer_status,
    get_transfer_outcome,
    get_network_summary
)

def _gather_context_for_question(question: str) -> tuple[Dict[str, Any], List[str]]:
    context = {}
    tools_used = []

    # Detect SKU (e.g. YOG-001, MLK-001, BRD-001, etc.)
    sku_matches = re.findall(r'\b[A-Za-z0-9]{2,8}-\d{3,4}\b', question, re.IGNORECASE)
    # Detect Store (e.g. STORE_A, store_b, etc.)
    store_matches = re.findall(r'\bSTORE_[A-Za-z0-9]+\b', question, re.IGNORECASE)
    # Detect Transfer ID (e.g. TRF-..., TR-...)
    transfer_matches = re.findall(r'\b(?:TRF|TR)-[A-Za-z0-9]+\b', question, re.IGNORECASE)

    sku_id = sku_matches[0].upper() if sku_matches else None
    store_id = store_matches[0].upper() if store_matches else None
    transfer_id = transfer_matches[0].upper() if transfer_matches else None

    if sku_id:
        target_store = store_id or "STORE_A"
        risk = get_inventory_risk(sku_id, target_store)
        context["inventory_risk"] = risk
        tools_used.append("get_inventory_risk")

        if not risk.get("error"):
            decision = evaluate_recovery_options(sku_id, target_store)
            context["recovery_options"] = decision
            tools_used.append("evaluate_recovery_options")

            destinations = find_destination_matches(sku_id, target_store)
            context["destination_matches"] = destinations
            tools_used.append("find_destination_matches")

    elif transfer_id:
        status = get_transfer_status(transfer_id)
        context["transfer_status"] = status
        tools_used.append("get_transfer_status")

        outcome = get_transfer_outcome(transfer_id)
        context["transfer_outcome"] = outcome
        tools_used.append("get_transfer_outcome")

    else:
        summary = get_network_summary()
        context["network_summary"] = summary
        tools_used.append("get_network_summary")

    return context, tools_used

def _extract_answer_text(result: Any) -> str:
    if not result:
        return "No response generated."
    msg = getattr(result, "message", None)
    if msg:
        if isinstance(msg, dict):
            content = msg.get("content", [])
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    return block["text"]
                elif hasattr(block, "text") and block.text:
                    return block.text
        elif hasattr(msg, "content"):
            for block in msg.content:
                if hasattr(block, "text") and block.text:
                    return block.text
                elif isinstance(block, dict) and "text" in block:
                    return block["text"]
    if hasattr(result, "text") and result.text:
        return result.text
    return str(result)

def ask_restock_agent(question: str) -> Dict[str, Any]:
    try:
        model_name = get_configured_model_name()
        if not model_supports_tools(model_name):
            context, tools_used = _gather_context_for_question(question)
            agent_no_tools = create_restock_agent(include_tools=False)
            
            augmented_prompt = (
                f"User Question: {question}\n\n"
                f"Deterministic Context from ReStockAI Engines:\n"
                f"{json.dumps(context, indent=2, default=str)}\n\n"
                f"Answer the user question concisely and accurately citing only the numbers and calculations from the deterministic engine above."
            )
            result = agent_no_tools(augmented_prompt)
            answer_text = _extract_answer_text(result)
            return {
                "question": question,
                "answer": answer_text,
                "tools_used": tools_used
            }

        agent = create_restock_agent()
        try:
            result = agent(question)
            answer_text = _extract_answer_text(result)
            return {
                "question": question,
                "answer": answer_text,
                "tools_used": []
            }
        except Exception as tool_err:
            err_msg = str(tool_err).lower()
            if "does not support tools" in err_msg or "tool" in err_msg:
                context, tools_used = _gather_context_for_question(question)
                agent_no_tools = create_restock_agent(include_tools=False)
                
                augmented_prompt = (
                    f"User Question: {question}\n\n"
                    f"Deterministic Context from ReStockAI Engines:\n"
                    f"{json.dumps(context, indent=2, default=str)}\n\n"
                    f"Answer the user question concisely and accurately citing only the numbers and calculations from the deterministic engine above."
                )
                result = agent_no_tools(augmented_prompt)
                answer_text = _extract_answer_text(result)
                return {
                    "question": question,
                    "answer": answer_text,
                    "tools_used": tools_used
                }
            raise tool_err

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
