"""Real-provider integration tests (OpenAI-compatible), no network needed.

Uses httpx.MockTransport so the OpenAIProvider/OpenAIEmbedder request/response
handling is verified deterministically without an API key or internet.
"""
from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import settings
from app.providers.embeddings.openai_embeddings import OpenAIEmbedder
from app.providers.llm.base import ProviderUnavailableError, get_provider
from app.providers.llm.openai_provider import OpenAIProvider


def _chat_handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path.endswith("/chat/completions")
    body = json.loads(request.content)
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["role"] == "user"
    return httpx.Response(
        200,
        json={
            "model": body["model"],
            "choices": [
                {"message": {"role": "assistant", "content": "Real LLM answer"}}
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 4},
        },
        headers={"Content-Type": "application/json"},
    )


def _embeddings_handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path.endswith("/embeddings")
    body = json.loads(request.content)
    n = len(body["input"])
    return httpx.Response(
        200,
        json={
            "data": [
                {"index": i, "embedding": [0.1 * (i + 1)] * 4} for i in range(n)
            ]
        },
        headers={"Content-Type": "application/json"},
    )


def test_openai_provider_generates_with_usage():
    provider = OpenAIProvider(
        api_key="test-key",
        transport=httpx.MockTransport(_chat_handler),
    )
    response = provider.generate("hello", "mock-large", system="be brief")
    assert response.text == "Real LLM answer"
    # mock-large maps onto the strong model tier
    assert response.model == "gpt-4o"
    assert response.input_tokens == 11
    assert response.output_tokens == 4
    assert response.latency_ms >= 0


def test_openai_provider_missing_key_raises_clean_error():
    provider = OpenAIProvider(api_key="", transport=httpx.MockTransport(_chat_handler))
    with pytest.raises(ProviderUnavailableError, match="OPENAI_API_KEY"):
        provider.generate("hello", "mock-small")


def test_openai_provider_bad_credentials_fail_fast():
    calls = {"n": 0}

    def unauthorized(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    provider = OpenAIProvider(
        api_key="wrong", transport=httpx.MockTransport(unauthorized)
    )
    with pytest.raises(ProviderUnavailableError, match="credentials"):
        provider.generate("hello", "mock-small")
    assert calls["n"] == 1  # 401 fails fast, no retry burn


def test_openai_provider_retries_on_429_then_succeeds():
    state = {"n": 0}

    def flaky(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(429, json={"error": "slow down"})
        return httpx.Response(
            200,
            json={
                "model": "gpt-4o-mini",
                "choices": [
                    {"message": {"role": "assistant", "content": "Real LLM answer"}}
                ],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            },
        )

    provider = OpenAIProvider(api_key="test-key", transport=httpx.MockTransport(flaky))
    response = provider.generate("hello", "mock-small")
    assert response.text == "Real LLM answer"
    assert state["n"] == 2


def test_openai_provider_factory_branch():
    provider = get_provider("openai")
    assert provider.provider_name == "openai"


def test_settings_expose_openai_fields():
    assert settings.openai_base_url.startswith("https://")
    assert settings.openai_cheap_model
    assert settings.openai_strong_model
    assert settings.openai_embedding_model


def test_openai_embedder_returns_ordered_vectors():
    embedder = OpenAIEmbedder(
        api_key="test-key",
        transport=httpx.MockTransport(_embeddings_handler),
    )
    # The API shuffles indexes; the provider must restore input order.
    vectors = embedder.embed(["a", "b", "c"])
    assert len(vectors) == 3
    assert vectors[0] == pytest.approx([0.1] * 4)
    assert vectors[2] == pytest.approx([0.3] * 4)


def test_openai_embedder_missing_key_raises():
    embedder = OpenAIEmbedder(api_key="", transport=httpx.MockTransport(_embeddings_handler))
    with pytest.raises(ProviderUnavailableError, match="OPENAI_API_KEY"):
        embedder.embed(["x"])
