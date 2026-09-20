import os
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

def create_restock_agent() -> Agent:
    host = os.getenv("RESTOCKAI_OLLAMA_HOST", "http://localhost:11434")
    model_name = os.getenv("RESTOCKAI_AGENT_MODEL", "llama3.1")
    temperature_str = os.getenv("RESTOCKAI_AGENT_TEMPERATURE", "0.2")
    
    try:
        temperature = float(temperature_str)
    except ValueError:
        temperature = 0.2

    # Configure the Ollama model instance
    model = OllamaModel(
        model_name=model_name,
        endpoint=host,
        temperature=temperature
    )

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[
            get_inventory_risk,
            find_destination_matches,
            evaluate_recovery_options,
            optimize_logistics,
            get_transfer_status,
            get_transfer_outcome,
            get_network_summary
        ]
    )
    
    return agent
