"""OpenAI embeddings provider (real-integration path).

``POST {base_url}/embeddings`` with model ``OPENAI_EMBEDDING_MODEL``
(default ``text-embedding-3-small``). Activated with::

    EMBEDDING_PROVIDER=openai
    OPENAI_API_KEY=sk-...

Results are returned ordered by the API's ``index`` field so callers always
get vectors aligned with the input texts.
"""
from __future__ import annotations

import httpx

from app.providers import get_setting
from app.providers.embeddings.base import Embedder
from app.providers.llm.base import ProviderUnavailableError

__all__ = ["OpenAIEmbedder", "DEFAULT_EMBEDDING_MODEL"]

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class OpenAIEmbedder(Embedder):
    """OpenAI-compatible embeddings provider."""

    provider_name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = (api_key or get_setting("openai_api_key", "") or "").strip()
        self._base_url = (
            base_url
            or get_setting("openai_base_url", "https://api.openai.com/v1")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self._model = model or get_setting(
            "openai_embedding_model", DEFAULT_EMBEDDING_MODEL
        )
        self._timeout = float(timeout_seconds or 30.0)
        self._transport = transport

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self._api_key:
            raise ProviderUnavailableError(
                "OpenAI embedder selected but OPENAI_API_KEY is not configured"
            )

        payload = {"model": self._model, "input": list(texts)}
        with httpx.Client(
            base_url=self._base_url,
            timeout=self._timeout,
            transport=self._transport,
        ) as client:
            response = client.post(
                "/embeddings",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
        if response.status_code in (401, 403):
            raise ProviderUnavailableError(
                "OpenAI rejected the credentials (HTTP "
                f"{response.status_code}); check OPENAI_API_KEY"
            )
        response.raise_for_status()

        data = response.json().get("data") or []
        ordered = sorted(data, key=lambda item: int(item.get("index") or 0))
        vectors: list[list[float]] = [item.get("embedding") or [] for item in ordered]
        if len(vectors) != len(texts):
            raise ProviderUnavailableError(
                f"OpenAI embeddings returned {len(vectors)} vectors for "
                f"{len(texts)} inputs"
            )
        return vectors
