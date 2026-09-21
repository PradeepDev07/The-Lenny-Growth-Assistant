import json
import time
import logging
from typing import AsyncIterator, List, Optional
import httpx

from backend.app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger("lenny-growth-assistant.llm.ollama")


class OllamaProvider(BaseLLMProvider):
    """
    Local offline LLM provider communicating with Ollama's REST API.
    """

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama3.2:3b"):
        super().__init__(model_name=model_name)
        self.base_url = base_url.rstrip("/")

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    def _build_payload(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> dict:
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            formatted_messages.append({"role": msg.role, "content": msg.content})

        return {
            "model": self.model_name,
            "messages": formatted_messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

    async def generate(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> LLMResponse:
        payload = self._build_payload(messages, system_prompt, stream=False, temperature=temperature, max_tokens=max_tokens)
        start_time = time.perf_counter()

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            content = data.get("message", {}).get("content", "")
            prompt_tokens = data.get("prompt_eval_count", 0)
            completion_tokens = data.get("eval_count", 0)

            return LLMResponse(
                text=content,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=round(latency_ms, 2),
                provider="ollama",
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
        payload = self._build_payload(messages, system_prompt, stream=True, temperature=temperature, max_tokens=max_tokens)

        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise RuntimeError(f"Ollama stream error HTTP {response.status_code}: {error_text.decode('utf-8')}")

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue
