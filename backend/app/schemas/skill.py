from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EssayRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=2,
        description="The growth, product, or startup topic to write an essay on"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID to link this essay and conversation messages to"
    )
    provider_override: Optional[str] = Field(
        default=None,
        description="Optional model provider override ('ollama', 'gemini', 'openrouter')"
    )


class EssayResponse(BaseModel):
    title: str
    session_id: str
    artifact_id: Optional[str] = None
    content: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    model_info: Dict[str, Any] = Field(default_factory=dict)
