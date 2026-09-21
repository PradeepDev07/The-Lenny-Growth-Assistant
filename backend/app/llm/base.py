from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional
from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: str = Field(..., description="user, assistant, or system")
    content: str = Field(..., description="Text content of the message")


class LLMResponse(BaseModel):
    """
    Normalized response structure across all LLM providers.
    Insulates upstream business logic from vendor-specific payloads.
    """
    text: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    provider: str
    model: str
    fallback_used: bool = False


class BaseLLMProvider(ABC):
    """
    Abstract Base Class for all LLM providers (Liskov Substitution Principle).
    """

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    async def is_available(self) -> bool:
        """Checks if the provider credentials and network endpoint are currently reachable."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> LLMResponse:
        """Executes a non-streaming completion and returns normalized LLMResponse."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        """Yields raw string tokens asynchronously as they arrive from the model."""
        pass
