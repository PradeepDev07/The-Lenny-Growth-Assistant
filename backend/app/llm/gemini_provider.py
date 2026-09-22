import json
import time
import logging
from typing import AsyncIterator, List, Optional
import httpx

from backend.app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger("lenny-growth-assistant.llm.gemini")


class GeminiProvider(BaseLLMProvider):
    """
    Direct Google Gemini API client via REST endpoints.
    Excels at large-context retrieval Q&A and low-latency grounded reasoning.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-flash-latest"):
        super().__init__(model_name=model_name)
        self.api_key = api_key.strip() if api_key else ""
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    def _build_payload(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192
    ) -> dict:
        contents = []
        for msg in messages:
            # Map role: 'user' -> 'user', 'assistant' -> 'model'
            role = "model" if msg.role == "assistant" else "user"
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })

        gen_config = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        # Only set thinkingBudget for models that support thinkingConfig (omit for lite models)
        if "lite" not in self.model_name.lower():
            gen_config["thinkingConfig"] = {
                "thinkingBudget": 0
            }

        payload = {
            "contents": contents,
            "generationConfig": gen_config
        }

        if system_prompt:
            payload["system_instruction"] = {
                "parts": [{"text": system_prompt}]
            }

        return payload

    async def generate(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        url = f"{self.base_url}/{self.model_name}:generateContent?key={self.api_key}"
        payload = self._build_payload(messages, system_prompt, temperature=temperature, max_tokens=max_tokens)
        start_time = time.perf_counter()

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            candidates = data.get("candidates", [])
            text_parts = []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    if "text" in part:
                        text_parts.append(part["text"])

            text = "".join(text_parts)
            usage = data.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", 0)
            completion_tokens = usage.get("candidatesTokenCount", 0)

            return LLMResponse(
                text=text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=round(latency_ms, 2),
                provider="gemini",
                model=self.model_name,
                fallback_used=False
            )

    async def stream(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192
    ) -> AsyncIterator[str]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        url = f"{self.base_url}/{self.model_name}:streamGenerateContent?alt=sse&key={self.api_key}"
        payload = self._build_payload(messages, system_prompt, temperature=temperature, max_tokens=max_tokens)

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise RuntimeError(f"Gemini stream error HTTP {response.status_code}: {error_text.decode('utf-8')}")

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if not data_str:
                        continue
                    try:
                        chunk = json.loads(data_str)
                        candidates = chunk.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                if "text" in part and part["text"]:
                                    yield part["text"]
                    except json.JSONDecodeError:
                        continue
