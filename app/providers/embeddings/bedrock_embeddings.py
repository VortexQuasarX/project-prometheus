"""Amazon Titan embedding provider via Bedrock (production path).

Lazy ``import boto3``; raises ``ProviderUnavailableError`` cleanly when
boto3 or AWS credentials are missing, or in mock mode. Mirrors the LLM
provider reliability contract: 10s timeouts and retries with exponential
backoff (2 attempts, 0.2s/0.4s schedule) on transient failures only.
"""
from __future__ import annotations

import json
import math
import time
from typing import Any

from app.providers import TransientProviderError, classify_boto_error, get_setting
from app.providers.embeddings.base import Embedder
from app.providers.llm.base import ProviderUnavailableError

__all__ = ["BedrockEmbedder", "DEFAULT_TITAN_EMBEDDING_MODEL_ID"]

#: Titan embeddings model (normalized 1536-dim output).
DEFAULT_TITAN_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"

_ATTEMPTS = 2
_BACKOFF_BASE_S = 0.2


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0.0:
        return vector
    return [value / norm for value in vector]


class BedrockEmbedder(Embedder):
    """Bedrock Titan embeddings (production path; inert without credentials)."""

    provider_name = "bedrock"

    def __init__(
        self,
        model_id: str | None = None,
        region_name: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._model_id = (
            model_id
            or get_setting("bedrock_embedding_model_id", "")
            or DEFAULT_TITAN_EMBEDDING_MODEL_ID
        )
        import os
        self._region = (
            region_name
            or get_setting("bedrock_region", "")
            or os.environ.get("AWS_REGION", "")
            or get_setting("aws_region", "")
            or "ap-south-1"
        )
        self._timeout = float(timeout_seconds or 10.0)
        self._client: Any = None  # lazy boto3 client

    # ------------------------------------------------------------------
    # Embedder
    # ------------------------------------------------------------------
    def embed(self, texts: list[str]) -> list[list[float]]:
        self._ensure_mode()
        client = self._ensure_client()
        return [self._invoke_one(client, text) for text in texts]

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _ensure_mode(self) -> None:
        """Never run in mock mode (contract): fail fast with a clean message."""
        if (get_setting("embedding_provider", "mock") or "mock").strip().lower() != "bedrock":
            raise ProviderUnavailableError(
                "BedrockEmbedder must not run in mock mode. Set EMBEDDING_PROVIDER=bedrock "
                "and configure AWS credentials to enable the production path."
            )

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise ProviderUnavailableError(
                "boto3 is not installed; install it with `pip install boto3` to use "
                "Bedrock embeddings."
            ) from exc
        config = Config(
            connect_timeout=self._timeout,
            read_timeout=self._timeout,
            retries={"max_attempts": 0, "mode": "standard"},  # we own the retries
        )
        try:
            self._client = boto3.client(
                "bedrock-runtime", region_name=self._region, config=config
            )
        except Exception as exc:  # noqa: BLE001 - controlled surface
            raise ProviderUnavailableError(f"Failed to initialize the Bedrock client: {exc}") from exc
        return self._client

    def _invoke_one(self, client: Any, text: str) -> list[float]:
        last_exc: BaseException | None = None
        for attempt in range(_ATTEMPTS):
            try:
                response = client.invoke_model(
                    modelId=self._model_id,
                    body=json.dumps({"inputText": text}),
                    accept="application/json",
                    contentType="application/json",
                )
                payload = json.loads(response["body"].read())
                embedding = payload.get("embedding")
                if not isinstance(embedding, list) or not embedding:
                    raise ProviderUnavailableError(
                        f"Unexpected Titan embedding response: {payload!r}"
                    )
                return _l2_normalize([float(value) for value in embedding])
            except Exception as exc:  # noqa: BLE001 - classified below
                classified = classify_boto_error(exc)
                if isinstance(classified, TransientProviderError):
                    last_exc = classified
                    if attempt < _ATTEMPTS - 1:
                        time.sleep(_BACKOFF_BASE_S * (2**attempt))
                    continue
                raise classified from None
        raise ProviderUnavailableError(
            f"Bedrock embedding request failed after {_ATTEMPTS} attempts: {last_exc}"
        )
