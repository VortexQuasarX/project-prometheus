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

#: Default cheap tier (Amazon Nova Micro — first party, no marketplace credit-card block).
DEFAULT_HAIKU_MODEL_ID = "apac.amazon.nova-micro-v1:0"
#: Default strong tier (Amazon Nova Lite — first party, no marketplace credit-card block).
DEFAULT_SONNET_MODEL_ID = "apac.amazon.nova-lite-v1:0"

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
        model_id = self._resolve_model_id(model)
        target_region = self._resolve_region_for_model(model_id)
        client = self._ensure_client(target_region)

        started = time.perf_counter()
        
        # 1. Attempt Bedrock Converse API (Universal cross-vendor API)
        try:
            converse_kwargs: dict[str, Any] = {
                "modelId": model_id,
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {
                    "maxTokens": max(1, int(max_tokens or 500)),
                    "temperature": float(temperature),
                },
            }
            if system:
                converse_kwargs["system"] = [{"text": system}]

            payload = self._converse_with_retries(client, converse_kwargs)
            latency_ms = max(0, int((time.perf_counter() - started) * 1000))

            text = (
                payload.get("output", {})
                .get("message", {})
                .get("content", [{}])[0]
                .get("text", "")
            )
            usage = payload.get("usage") or {}
            input_tokens = int(usage.get("inputTokens", 0) or 0)
            output_tokens = int(usage.get("outputTokens", 0) or 0)

            return LLMResponse(
                text=text,
                model=model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
            )
        except Exception as conv_exc:
            # Fall back to legacy invoke_model if converse is not supported for this model ID
            is_nova = "nova" in model_id.lower()
            if is_nova:
                body: dict[str, Any] = {
                    "messages": [{"role": "user", "content": [{"text": prompt}]}],
                    "inferenceConfig": {
                        "max_new_tokens": max(1, int(max_tokens or 500)),
                        "temperature": float(temperature),
                    },
                }
                if system:
                    body["system"] = [{"text": system}]
            else:
                body = {
                    "anthropic_version": _ANTHROPIC_VERSION,
                    "max_tokens": max(1, int(max_tokens or 500)),
                    "temperature": float(temperature),
                    "messages": [{"role": "user", "content": prompt}],
                }
                if system:
                    body["system"] = system

            payload = self._invoke_with_retries(client, body, model_id)
            latency_ms = max(0, int((time.perf_counter() - started) * 1000))

            if is_nova:
                text = (
                    payload.get("output", {})
                    .get("message", {})
                    .get("content", [{}])[0]
                    .get("text", "")
                )
                usage = payload.get("usage") or {}
                input_tokens = int(usage.get("inputTokens", 0) or 0)
                output_tokens = int(usage.get("outputTokens", 0) or 0)
            else:
                content = payload.get("content") or []
                text = "".join(
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                )
                usage = payload.get("usage") or {}
                input_tokens = int(usage.get("input_tokens", 0) or 0)
                output_tokens = int(usage.get("output_tokens", 0) or 0)

            return LLMResponse(
                text=text,
                model=model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
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

    def _resolve_region_for_model(self, model_id: str) -> str:
        """Dynamically resolve the AWS region for cross-region inference models."""
        mid_lower = (model_id or "").lower()
        if mid_lower.startswith("us.") or "palmyra" in mid_lower or "mistral-small" in mid_lower or "nova-2-lite" in mid_lower:
            return "us-east-1"
        if "2407" in mid_lower or "llama3-1-8b" in mid_lower:
            return "us-west-2"
        if "next" in mid_lower:
            return "ap-southeast-2"
        return self._region

    def _ensure_client(self, region: str | None = None) -> Any:
        target_region = region or self._region
        if not hasattr(self, "_clients"):
            self._clients: dict[str, Any] = {}
        if target_region in self._clients:
            return self._clients[target_region]
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
            client = boto3.client(
                "bedrock-runtime", region_name=target_region, config=config
            )
            self._clients[target_region] = client
            return client
        except Exception as exc:  # noqa: BLE001 - controlled surface
            raise ProviderUnavailableError(f"Failed to initialize the Bedrock client for {target_region}: {exc}") from exc

    def _resolve_model_id(self, model: str) -> str:
        model_clean = (model or "").strip()
        model_lower = model_clean.lower()
        # Pass through any model containing vendor dots/colons or known provider names
        known_prefixes = (
            "amazon", "anthropic", "apac", "global", "meta", "google",
            "deepseek", "mistral", "qwen", "nvidia", "zai", "moonshot", "titan", "us", "writer", "openai"
        )
        if model_clean and ("." in model_clean or ":" in model_clean or any(p in model_lower for p in known_prefixes)):
            return model_clean

        generic = (get_setting("bedrock_model_id", "") or "").strip()
        # Cheap tier: Nova Micro
        if "cheap" in model_lower or "haiku" in model_lower or "micro" in model_lower or "small" in model_lower:
            return (get_setting("bedrock_cheap_model_id", "") or generic or DEFAULT_HAIKU_MODEL_ID)
        # Premium tier: Nova Pro (most capable)
        if "pro" in model_lower or "premium" in model_lower:
            return (get_setting("bedrock_premium_model_id", "") or "apac.amazon.nova-pro-v1:0")
        # Strong tier: Nova Lite
        if "strong" in model_lower or "sonnet" in model_lower or "lite" in model_lower or "large" in model_lower:
            return (get_setting("bedrock_strong_model_id", "") or generic or DEFAULT_SONNET_MODEL_ID)
        # Unknown/empty model -> strongest sensible gateway default.
        return generic or DEFAULT_SONNET_MODEL_ID

    def _converse_with_retries(self, client: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Invoke Bedrock Converse API with exponential backoff."""
        last_exc: BaseException | None = None
        for attempt in range(_ATTEMPTS):
            try:
                return client.converse(**kwargs)
            except Exception as exc:
                classified = classify_boto_error(exc)
                if isinstance(classified, TransientProviderError):
                    last_exc = classified
                    if attempt < _ATTEMPTS - 1:
                        time.sleep(_BACKOFF_BASE_S * (2**attempt))
                    continue
                raise classified from None
        raise ProviderUnavailableError(
            f"Bedrock converse request failed after {_ATTEMPTS} attempts: {last_exc}"
        )

    def _invoke_with_retries(self, client: Any, body: dict[str, Any], model_id: str) -> dict[str, Any]:
        """Invoke Bedrock invoke_model with exponential backoff."""
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
