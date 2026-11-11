import os
from strands import Agent
from .llm import get_llm_model

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
    model = get_llm_model()

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
