"""Provider layer facade for Project Prometheus.

The heavy lifting lives in the subpackages:

- ``app.providers.llm``        - LLM provider abstraction (mock + Bedrock)
- ``app.providers.embeddings`` - embedding abstraction (mock + Bedrock Titan)

This package also owns shared *provider plumbing* used across the LLM,
embedding, vector-store, cache and RAG slices:

- :func:`get_setting` - single, stable config shim: it prefers the project's
  ``app.core.config.get_settings()`` object and falls back to environment
  variables, so provider modules stay importable even before the config
  module is fully assembled (parallel-build contract).
- :func:`retry_with_backoff` - deterministic exponential-backoff retry loop
  (2 attempts, 0.2s/0.4s schedule) used by the Bedrock providers.
- :class:`TransientProviderError` / :func:`classify_boto_error` - controlled
  error mapping for boto3/botocore failures (retryable vs credential/config).
"""
from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any, TypeVar

__all__ = [
    "TransientProviderError",
    "classify_boto_error",
    "get_setting",
    "retry_with_backoff",
    "__version__",
]

__version__ = "0.1.0"

_T = TypeVar("_T")

#: AWS error codes that are safe to retry (throttles, 5xx, timeouts).
_RETRYABLE_ERROR_CODES = frozenset(
    {
        "ThrottlingException",
        "Throttling",
        "TooManyRequestsException",
        "ServiceUnavailable",
        "InternalServerError",
        "SlowDown",
        "RequestTimeout",
        "ModelTimeoutException",
        "ModelStreamErrorException",
        "TransientException",
    }
)


class TransientProviderError(RuntimeError):
    """Signals a retryable provider failure (throttle, timeout, 5xx)."""


def get_setting(name: str, default: Any = None) -> Any:
    """Return a settings value by attribute name.

    Prefers ``app.core.config.get_settings()`` (the project contract); falls
    back to the uppercase environment variable (``name`` is the lowercase
    pydantic-settings attribute, e.g. ``llm_provider`` -> ``LLM_PROVIDER``)
    and finally to ``default``.
    """
    try:
        from app.core.config import get_settings

        return getattr(get_settings(), name, default)
    except Exception:  # noqa: BLE001 - config not assembled yet; env fallback
        return os.environ.get(name.upper(), default)


def retry_with_backoff(
    fn: Callable[[], _T],
    *,
    attempts: int = 2,
    base_delay: float = 0.2,
    sleep: Callable[[float], None] = time.sleep,
) -> _T:
    """Call ``fn`` with exponential backoff between attempts.

    Deterministic (no jitter) so tests stay reproducible. Defaults match the
    Bedrock contract: 2 attempts on an exponential 0.2s / 0.4s schedule
    (0.2s before the retry; 0.4s would precede a third attempt if configured).
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    last_exc: BaseException | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - re-raised below
            last_exc = exc
            if attempt < attempts - 1:
                sleep(base_delay * (2**attempt))
    assert last_exc is not None
    raise last_exc


def classify_boto_error(exc: BaseException) -> BaseException:
    """Map a boto3/botocore exception to a controlled exception.

    - missing/invalid credentials        -> ``ProviderUnavailableError``
    - throttling / 5xx / timeout         -> ``TransientProviderError`` (retry)
    - other ClientError                  -> ``ProviderUnavailableError``
    - anything else                      -> returned unchanged
    """
    from app.providers.llm.base import ProviderUnavailableError

    try:
        from botocore.exceptions import (  # type: ignore[import-not-found]
            BotoCoreError,
            ClientError,
            NoCredentialsError,
            PartialCredentialsError,
        )
    except ImportError:
        return exc

    if isinstance(exc, (NoCredentialsError, PartialCredentialsError)):
        return ProviderUnavailableError(
            "AWS credentials are not configured; set AWS_ACCESS_KEY_ID / "
            "AWS_SECRET_ACCESS_KEY or attach an IAM role before calling the "
            "Bedrock provider."
        )
    if isinstance(exc, ClientError):
        error = (exc.response or {}).get("Error", {})
        code = str(error.get("Code", ""))
        if code in _RETRYABLE_ERROR_CODES:
            return TransientProviderError(f"{code}: {exc}")
        return ProviderUnavailableError(f"Bedrock API error ({code}): {exc}")
    if isinstance(exc, BotoCoreError):
        return TransientProviderError(f"Bedrock connection error: {exc}")
    return exc
