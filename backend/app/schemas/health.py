from pydantic import BaseModel, Field
from typing import Dict, List


class HealthResponse(BaseModel):
    """
    Readiness & Liveness probe response contract.
    Must truthfully report downstream dependency readiness.
    """
    status: str = Field(..., description="Overall system health: healthy or degraded")
    db: bool = Field(..., description="Relational database connectivity state")
    ollama: bool = Field(..., description="Local Ollama daemon availability")
    cloud_llm_configured: bool = Field(..., description="Whether at least one cloud LLM API key is present")
    version: str = Field(..., description="Application version")


class ProviderStatus(BaseModel):
    configured: bool
    default_model: str


class PublicConfigResponse(BaseModel):
    """
    Publicly safe runtime configuration for the client UI.
    Never exposes API keys or sensitive credentials.
    """
    environment: str
    version: str
    cloud_llm_configured: bool
    providers: Dict[str, ProviderStatus]
    task_routing: Dict[str, str]
    cors_origins: List[str]
