import json
import time
import logging
from typing import AsyncIterator, List, Optional
import httpx

from backend.app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger("lenny-growth-assistant.llm.openrouter")


class OpenRouterProvider(BaseLLMProvider):
    """
    OpenRouter multi-model provider accessing high-capability models
    (Claude 3.7 Sonnet, GPT-4o, Llama 3.3) for long-form essays and structured skills.
    """

    def __init__(self, api_key: str, model_name: str = "anthropic/claude-3.7-sonnet"):
        super().__init__(model_name=model_name)
        self.api_key = api_key.strip() if api_key else ""
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://lennygrowth.local",
            "X-Title": "The Lenny Growth Assistant",
            "Content-Type": "application/json"
        }

    def _build_payload(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> dict:
        formatted = []
        if system_prompt:
            formatted.append({"role": "system", "content": system_prompt})
        for msg in messages:
            formatted.append({"role": msg.role, "content": msg.content})

        return {
            "model": self.model_name,
            "messages": formatted,
            "stream": stream,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

    async def generate(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured")

        payload = self._build_payload(messages, system_prompt, stream=False, temperature=temperature, max_tokens=max_tokens)
        headers = self._build_headers()
        start_time = time.perf_counter()

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(self.base_url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenRouter API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            return LLMResponse(
                text=content,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=round(latency_ms, 2),
                provider="openrouter",
                model=self.model_name,
                fallback_used=False
            )

    async def stream(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured")

        payload = self._build_payload(messages, system_prompt, stream=True, temperature=temperature, max_tokens=max_tokens)
        headers = self._build_headers()

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", self.base_url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise RuntimeError(f"OpenRouter stream error HTTP {response.status_code}: {error_text.decode('utf-8')}")

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                    except json.JSONDecodeError:
                        continue
