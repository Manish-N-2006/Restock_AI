import os
import requests
from strands import Agent
from strands.models.ollama import OllamaModel

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

def model_supports_tools(model_name: str) -> bool:
    name_lower = model_name.lower()
    tool_models = ["llama3.1", "llama3.2", "qwen2.5", "mistral", "command-r", "firefunction", "nemotron"]
    return any(m in name_lower for m in tool_models)

def get_configured_model_name(host: str = "http://localhost:11434") -> str:
    env_model = os.getenv("RESTOCKAI_AGENT_MODEL")
    if env_model:
        return env_model

    try:
        res = requests.get(f"{host}/api/tags", timeout=2)
        if res.status_code == 200:
            models = res.json().get("models", [])
            names = [m.get("name", "") for m in models]
            for candidate in ["llama3.1", "llama3.2", "llama3:latest", "llama3:8b", "llama3"]:
                for n in names:
                    if n.startswith(candidate) or candidate in n:
                        return n
            if names:
                return names[0]
    except Exception:
        pass

    return "llama3:latest"

def create_restock_agent(include_tools: bool = True) -> Agent:
    host = os.getenv("RESTOCKAI_OLLAMA_HOST", "http://localhost:11434")
    model_name = get_configured_model_name(host)
    temperature_str = os.getenv("RESTOCKAI_AGENT_TEMPERATURE", "0.2")
    
    try:
        temperature = float(temperature_str)
    except ValueError:
        temperature = 0.2

    # Configure the Ollama model instance with host and model_id
    model = OllamaModel(
        host=host,
        model_id=model_name,
        temperature=temperature
    )

    tools = []
    if include_tools:
        tools = [
            get_inventory_risk,
            find_destination_matches,
            evaluate_recovery_options,
            optimize_logistics,
            get_transfer_status,
            get_transfer_outcome,
            get_network_summary
        ]

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=tools
    )
    
    return agent
