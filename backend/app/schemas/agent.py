from pydantic import BaseModel
from typing import List, Optional

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    question: str
    answer: str
    tools_used: List[str] = []

class HealthResponse(BaseModel):
    configured: bool
    available: bool
    model_provider: str
    ollama_host: str
    model_name: str
