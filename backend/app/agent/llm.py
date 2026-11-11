import os
import logging
from typing import Optional, Any

try:
    from strands.models.openai import OpenAIModel
except Exception:
    OpenAIModel = None

try:
    from strands.models.ollama import OllamaModel
except Exception:
    OllamaModel = None

logger = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_OLLAMA_MODEL = "llama3.1"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def get_llm_model(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
) -> Any:
    """
    Constructs a Strands-compatible model instance supporting tool calling.
    Defaults to Groq API via Strands OpenAIModel, with clean Ollama fallback.
    """
    provider = provider or os.getenv("RESTOCKAI_LLM_PROVIDER", "groq").lower()

    if temperature is None:
        try:
            temperature = float(os.getenv("RESTOCKAI_AGENT_TEMPERATURE", "0.2"))
        except ValueError:
            temperature = 0.2

    if provider == "groq":
        api_key = (os.getenv("RESTOCKAI_GROQ_API_KEY") or os.getenv("GROQ_API_KEY") or "").strip()
        model_id = model_name or os.getenv("RESTOCKAI_AGENT_MODEL", DEFAULT_GROQ_MODEL)

        if not api_key:
            env = os.getenv("RESTOCKAI_ENV", "development").strip().lower()
            if env == "production":
                raise ValueError(
                    "RESTOCKAI_GROQ_API_KEY is required in production when RESTOCKAI_LLM_PROVIDER=groq."
                )
            ollama_host = os.getenv("RESTOCKAI_OLLAMA_HOST", "http://localhost:11434")
            logger.warning(
                "RESTOCKAI_GROQ_API_KEY is not configured. Falling back to Ollama (%s).",
                ollama_host,
            )
            return OllamaModel(
                host=ollama_host,
                model_id=DEFAULT_OLLAMA_MODEL,
                temperature=temperature,
            )

        client_args = {
            "base_url": os.getenv("RESTOCKAI_GROQ_BASE_URL", GROQ_BASE_URL),
            "api_key": api_key,
            "timeout": 30.0,
            "max_retries": 3,
        }

        return OpenAIModel(
            model_id=model_id,
            client_args=client_args,
            params={"temperature": temperature},
        )

    elif provider == "ollama":
        host = os.getenv("RESTOCKAI_OLLAMA_HOST", "http://localhost:11434")
        model_id = model_name or os.getenv("RESTOCKAI_AGENT_MODEL", DEFAULT_OLLAMA_MODEL)
        return OllamaModel(
            host=host,
            model_id=model_id,
            temperature=temperature,
        )

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
