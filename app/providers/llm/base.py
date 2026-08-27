"""LLM provider abstraction (fixed contract).

Shared with the chat-pipeline and agent slices:

    LLMResponse(text, model, input_tokens, output_tokens, latency_ms)
    LLMProvider.generate(prompt, model, *, system=None, max_tokens=500,
                         temperature=0.3) -> LLMResponse
    get_provider(name=None) -> LLMProvider   # selects mock | bedrock

``ProviderUnavailableError`` signals a provider that cannot serve requests
right now (missing dependency, missing credentials, wrong mode) with a
clean, user-safe message — the app must never crash on a missing AWS setup.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "ProviderUnavailableError",
    "SUPPORTED_PROVIDERS",
    "get_provider",
]

SUPPORTED_PROVIDERS = ("mock", "bedrock")


class ProviderUnavailableError(RuntimeError):
    """Raised when a provider cannot serve requests (no deps/credentials/mode)."""


@dataclass(frozen=True)
class LLMResponse:
    """A generated completion with token and latency accounting."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class LLMProvider(ABC):
    """Interface every LLM backend implements."""

    provider_name: str = "base"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        model: str,
        *,
        system: str | None = None,
        max_tokens: int = 500,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """Generate a completion for ``prompt`` on ``model``.

        ``system`` is the optional system prompt, ``max_tokens`` caps the
        output, ``temperature`` steers sampling (ignored by deterministic
        mock providers).
        """
        raise NotImplementedError


def get_provider(name: str | None = None) -> LLMProvider:
    """Factory: return the LLM provider selected by ``name`` or settings.

    ``settings.llm_provider`` (env ``LLM_PROVIDER``) chooses between
    ``mock`` (default, no AWS required) and ``bedrock`` (production path).
    """
    from app.providers import get_setting

    provider_name = (
        name or get_setting("llm_provider", "mock") or "mock"
    ).strip().lower()
    if provider_name == "mock":
        from app.providers.llm.mock_provider import MockLLMProvider

        return MockLLMProvider()
    if provider_name == "bedrock":
        from app.providers.llm.bedrock_provider import BedrockProvider

        return BedrockProvider()
    raise ValueError(
        f"Unknown LLM provider {provider_name!r}; expected one of {SUPPORTED_PROVIDERS}"
    )
