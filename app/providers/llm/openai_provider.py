"""OpenAI-compatible LLM provider (real-integration path).

Talks to any OpenAI-compatible ``/chat/completions`` endpoint (OpenAI itself,
Azure-style gateways, vLLM, OpenRouter, ...) using ``httpx`` — no extra SDK
dependency. Activated with::

    LLM_PROVIDER=openai
    OPENAI_API_KEY=sk-...
    # optional:
    OPENAI_BASE_URL=https://api.openai.com/v1
    OPENAI_CHEAP_MODEL=gpt-4o-mini
    OPENAI_STRONG_MODEL=gpt-4o

Policy model names map onto the two tiers so the Router Agent and policy
``allowed_models`` keep working unchanged:

- ``mock-small`` / ``openai-cheap`` / ``bedrock-cheap`` -> OPENAI_CHEAP_MODEL
- ``mock-large`` / ``openai-strong`` / ``bedrock-strong`` -> OPENAI_STRONG_MODEL

Any other model string is passed through verbatim (so callers may use any
model the endpoint serves). Retries: 2 attempts with 0.2s/0.4s backoff on
429/5xx/network errors; 401/403/404 fail fast as ``ProviderUnavailableError``.
"""
from __future__ import annotations

import time
from typing import Any

import httpx

from app.providers import TransientProviderError, get_setting
from app.providers.llm.base import LLMProvider, LLMResponse, ProviderUnavailableError

__all__ = ["OpenAIProvider", "DEFAULT_CHEAP_MODEL", "DEFAULT_STRONG_MODEL"]

DEFAULT_CHEAP_MODEL = "gpt-4o-mini"
DEFAULT_STRONG_MODEL = "gpt-4o"

_ATTEMPTS = 3
_BACKOFFS = (0.2, 0.4)
_RETRY_STATUS = {408, 429, 500, 502, 503, 504}


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible chat-completions provider."""

    provider_name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = (api_key or get_setting("openai_api_key", "") or "").strip()
        self._base_url = (
            base_url
            or get_setting("openai_base_url", "https://api.openai.com/v1")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self._timeout = float(timeout_seconds or 30.0)
        self._transport = transport

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _resolve_model(self, model: str) -> str:
        cheap = get_setting("openai_cheap_model", DEFAULT_CHEAP_MODEL) or DEFAULT_CHEAP_MODEL
        strong = get_setting("openai_strong_model", DEFAULT_STRONG_MODEL) or DEFAULT_STRONG_MODEL
        mapping = {
            "openai-cheap": cheap,
            "openai-strong": strong,
            "mock-small": cheap,
            "mock-large": strong,
            "bedrock-cheap": cheap,
            "bedrock-strong": strong,
        }
        resolved = mapping.get((model or "").strip().lower())
        return resolved or (model or cheap).strip()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._base_url,
            timeout=self._timeout,
            transport=self._transport,
        )

    # ------------------------------------------------------------------
    # LLMProvider
    # ------------------------------------------------------------------
    def generate(
        self,
        prompt: str,
        model: str,
        *,
        system: str | None = None,
        max_tokens: int = 500,
        temperature: float = 0.3,
    ) -> LLMResponse:
        if not self._api_key:
            raise ProviderUnavailableError(
                "OpenAI provider selected but OPENAI_API_KEY is not configured"
            )
        resolved = self._resolve_model(model)
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": resolved,
            "messages": messages,
            "max_tokens": max(1, int(max_tokens or 500)),
            "temperature": float(temperature),
        }

        started = time.perf_counter()
        last_error: Exception | None = None
        for attempt in range(_ATTEMPTS):
            try:
                with self._client() as client:
                    response = client.post("/chat/completions", json=payload)
                if response.status_code in (401, 403):
                    raise ProviderUnavailableError(
                        "OpenAI rejected the credentials (HTTP "
                        f"{response.status_code}); check OPENAI_API_KEY"
                    )
                if response.status_code == 404:
                    raise ProviderUnavailableError(
                        f"OpenAI model or endpoint not found (HTTP 404): {resolved}"
                    )
                if response.status_code in _RETRY_STATUS:
                    last_error = TransientProviderError(
                        f"OpenAI returned HTTP {response.status_code}"
                    )
                    if attempt < _ATTEMPTS - 1:
                        time.sleep(_BACKOFFS[min(attempt, len(_BACKOFFS) - 1)])
                    continue
                response.raise_for_status()

                data = response.json()
                usage = data.get("usage") or {}
                text = ((data.get("choices") or [{}])[0].get("message") or {}).get(
                    "content", ""
                ) or ""
                latency_ms = int((time.perf_counter() - started) * 1000)
                return LLMResponse(
                    text=text,
                    model=data.get("model") or resolved,
                    input_tokens=int(usage.get("prompt_tokens") or max(1, len(prompt) // 4)),
                    output_tokens=int(
                        usage.get("completion_tokens") or max(1, len(text) // 4)
                    ),
                    latency_ms=latency_ms,
                )
            except ProviderUnavailableError:
                raise
            except TransientProviderError as exc:
                last_error = exc
                if attempt < _ATTEMPTS - 1:
                    time.sleep(_BACKOFFS[min(attempt, len(_BACKOFFS) - 1)])
                    continue
            except httpx.TransportError as exc:
                last_error = TransientProviderError(f"OpenAI transport error: {exc}")
                if attempt < _ATTEMPTS - 1:
                    time.sleep(_BACKOFFS[min(attempt, len(_BACKOFFS) - 1)])
                    continue

        raise ProviderUnavailableError(
            f"OpenAI provider unavailable after {_ATTEMPTS} attempts: {last_error}"
        )
