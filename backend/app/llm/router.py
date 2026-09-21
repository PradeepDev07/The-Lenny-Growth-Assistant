import logging
import time
from typing import AsyncIterator, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse
from backend.app.llm.ollama_provider import OllamaProvider
from backend.app.llm.gemini_provider import GeminiProvider
from backend.app.llm.openrouter_provider import OpenRouterProvider
from backend.app.db.repository import SessionRepository

logger = logging.getLogger("lenny-growth-assistant.llm.router")


class TaskRouter:
    """
    Task-Based Model Router with Graceful Cascading Fallback.
    Matches the specific growth assistant action (QA, Essay, Artifact, Intent)
    to the optimal model tier, with automated local Ollama fallback.
    """

    def __init__(self):
        # Instantiate provider adapters
        self.ollama = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model_name=settings.OLLAMA_MODEL
        )
        self.gemini = GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL
        )
        self.openrouter = OpenRouterProvider(
            api_key=settings.OPENROUTER_API_KEY,
            model_name=settings.OPENROUTER_MODEL
        )

    def get_chain_for_task(self, task: str) -> List[BaseLLMProvider]:
        """
        Determines the ordered provider fallback chain for a given task.
        """
        if task == "offline_demo_mode":
            return [self.ollama]

        if task == "essay_generation":
            # Strong long-form models preferred for Ship 30 essay generation
            return [self.openrouter, self.gemini, self.ollama]

        if task in ("retrieval_qa", "artifact_generation", "intent_routing"):
            # High-context, low-latency models preferred for RAG and code synthesis
            return [self.gemini, self.openrouter, self.ollama]

        # Default fallback chain
        return [self.gemini, self.openrouter, self.ollama]

    async def generate(
        self,
        task: str,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        db: Optional[AsyncSession] = None
    ) -> LLMResponse:
        """
        Executes completion with automated cascading fallback across provider tiers.
        """
        chain = self.get_chain_for_task(task)
        last_error: Optional[Exception] = None

        for idx, provider in enumerate(chain):
            provider_name = provider.__class__.__name__
            is_fallback = idx > 0

            # Check provider readiness
            is_ready = await provider.is_available()
            if not is_ready:
                logger.info(
                    "Skipping provider %s for task '%s' (not available / missing credentials)",
                    provider_name, task
                )
                continue

            try:
                logger.info(
                    "Attempting task '%s' via %s (%s) [attempt %d/%d]",
                    task, provider_name, provider.model_name, idx + 1, len(chain)
                )
                start_time = time.perf_counter()
                response = await provider.generate(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                latency_ms = (time.perf_counter() - start_time) * 1000.0

                response.fallback_used = is_fallback

                # Log routing telemetry to database if session provided
                if db:
                    try:
                        await SessionRepository.log_routing(
                            db=db,
                            task=task,
                            provider=response.provider,
                            model=response.model,
                            latency_ms=latency_ms,
                            fallback_used=is_fallback
                        )
                    except Exception as log_err:
                        logger.warning("Failed to record routing telemetry: %s", log_err)

                return response

            except Exception as e:
                logger.warning(
                    "Provider %s failed for task '%s': %s. Cascading down fallback chain...",
                    provider_name, task, e
                )
                last_error = e
                continue

        raise RuntimeError(f"All providers in fallback chain for task '{task}' failed. Last error: {last_error}")

    async def get_streaming_provider(
        self,
        task: str
    ) -> Tuple[BaseLLMProvider, bool]:
        """
        Determines the first working provider for streaming.
        Returns (provider, fallback_used).
        """
        chain = self.get_chain_for_task(task)
        for idx, provider in enumerate(chain):
            if await provider.is_available():
                return provider, (idx > 0)
        raise RuntimeError(f"No available providers found for task '{task}'")


# Global router singleton
model_router = TaskRouter()
