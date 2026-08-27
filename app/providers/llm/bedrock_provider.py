"""Amazon Bedrock LLM provider (production path).

Lazy ``import boto3``; raises ``ProviderUnavailableError`` with a clean
message when boto3 is missing, AWS credentials are absent, or the app is
running in mock mode — the local app never breaks without AWS. Implements
retries with exponential backoff (2 attempts, 0.2s/0.4s schedule) and 10s
connect/read timeouts.

Model mapping (env-driven, ``BEDROCK_MODEL_ID`` as the generic override):

- ``bedrock-cheap``  -> BEDROCK_MODEL_ID or BEDROCK_CHEAP_MODEL_ID or a
                        Claude Haiku-class default
- ``bedrock-strong`` -> BEDROCK_MODEL_ID or BEDROCK_STRONG_MODEL_ID or a
                        Claude Sonnet-class default
"""
from __future__ import annotations

import json
import time
from typing import Any

from app.providers import TransientProviderError, classify_boto_error, get_setting
from app.providers.llm.base import LLMProvider, LLMResponse, ProviderUnavailableError

__all__ = ["BedrockProvider", "DEFAULT_HAIKU_MODEL_ID", "DEFAULT_SONNET_MODEL_ID"]

#: Claude Haiku-class default (cheap tier) — matching AWS Bedrock model IDs.
DEFAULT_HAIKU_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
#: Claude Sonnet-class default (strong tier).
DEFAULT_SONNET_MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

_ANTHROPIC_VERSION = "bedrock-2023-05-31"
_ATTEMPTS = 2
_BACKOFF_BASE_S = 0.2


class BedrockProvider(LLMProvider):
    """Bedrock-backed LLM provider (Anthropic Messages API shape)."""

    provider_name = "bedrock"

    def __init__(
        self,
        region_name: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._region = region_name or get_setting("aws_region", "us-east-1") or "us-east-1"
        self._timeout = float(timeout_seconds or 10.0)
        self._client: Any = None  # lazy boto3 client

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
        self._ensure_mode()
        client = self._ensure_client()
        model_id = self._resolve_model_id(model)

        body: dict[str, Any] = {
            "anthropic_version": _ANTHROPIC_VERSION,
            "max_tokens": max(1, int(max_tokens or 500)),
            "temperature": float(temperature),
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system

        started = time.perf_counter()
        payload = self._invoke_with_retries(client, body, model_id)
        latency_ms = max(0, int((time.perf_counter() - started) * 1000))

        content = payload.get("content") or []
        text = "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
        usage = payload.get("usage") or {}
        return LLMResponse(
            text=text,
            model=model_id,
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
            latency_ms=latency_ms,
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _ensure_mode(self) -> None:
        """Never run in mock mode (contract): fail fast with a clean message."""
        if (get_setting("llm_provider", "mock") or "mock").strip().lower() != "bedrock":
            raise ProviderUnavailableError(
                "BedrockProvider must not run in mock mode. Set LLM_PROVIDER=bedrock "
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
                "the Bedrock provider."
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

    def _resolve_model_id(self, model: str) -> str:
        model_lower = (model or "").strip().lower()
        generic = (get_setting("bedrock_model_id", "") or "").strip()
        if "cheap" in model_lower or "haiku" in model_lower:
            return (get_setting("bedrock_cheap_model_id", "") or generic or DEFAULT_HAIKU_MODEL_ID)
        if "strong" in model_lower or "sonnet" in model_lower:
            return (get_setting("bedrock_strong_model_id", "") or generic or DEFAULT_SONNET_MODEL_ID)
        # Unknown/empty model -> strongest sensible gateway default.
        return generic or DEFAULT_SONNET_MODEL_ID

    def _invoke_with_retries(self, client: Any, body: dict[str, Any], model_id: str) -> dict[str, Any]:
        """Invoke Bedrock with exponential backoff (2 attempts, 0.2/0.4s).

        Only transient failures (throttles, timeouts, 5xx) are retried;
        credential/config errors surface immediately as
        ``ProviderUnavailableError``.
        """
        last_exc: BaseException | None = None
        for attempt in range(_ATTEMPTS):
            try:
                response = client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body),
                    accept="application/json",
                    contentType="application/json",
                )
                return json.loads(response["body"].read())
            except Exception as exc:  # noqa: BLE001 - classified below
                classified = classify_boto_error(exc)
                if isinstance(classified, TransientProviderError):
                    last_exc = classified
                    if attempt < _ATTEMPTS - 1:
                        time.sleep(_BACKOFF_BASE_S * (2**attempt))
                    continue
                raise classified from None
        raise ProviderUnavailableError(
            f"Bedrock request failed after {_ATTEMPTS} attempts: {last_exc}"
        )
