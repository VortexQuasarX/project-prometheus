"""HTTP middleware: request context (X-Request-Id + timing) and sliding-window
rate limiting per API key.

Rate limiting is in-memory and single-process by design (documented in
docs/ARCHITECTURE.md): the MVP runs one uvicorn worker. Multi-worker-safe
parts (SQLite state, SSE outbox) are unaffected.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from collections import deque
from typing import Any

from starlette.datastructures import MutableHeaders
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.errors import error_response
from app.core.security import hash_api_key


def _scope_headers(scope: dict[str, Any]) -> dict[str, str]:
    return {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in (scope.get("headers") or [])
    }


class RequestContextMiddleware:
    """Pure-ASGI middleware: injects ``X-Request-Id`` (uuid4 hex) when absent,
    records timing in ``scope["state"]``, and stamps every response header.

    Implemented as raw ASGI (not BaseHTTPMiddleware) so streaming responses
    such as the SSE endpoint are never buffered.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = _scope_headers(scope)
        request_id = headers.get("x-request-id") or uuid.uuid4().hex
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        start = time.perf_counter()

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers.setdefault("X-Request-Id", request_id)
                response_headers.setdefault(
                    "X-Process-Time-Ms", f"{(time.perf_counter() - start) * 1000:.1f}"
                )
            await send(message)

        await self.app(scope, receive, send_wrapper)


class _SlidingWindowStore:
    """Per-key sliding window of request timestamps (last 60s).

    Supports two backends:
    - **In-memory** (default): single-process only, used for local dev/testing.
    - **Redis sorted sets**: distributed, atomic via Lua script, used when
      ``settings.redis_url`` is set. Enables multi-worker rate limiting.
    """

    # Lua script for atomic sliding-window check + record in Redis.
    # KEYS[1] = rate-limit key, ARGV[1] = window_start, ARGV[2] = now,
    # ARGV[3] = limit, ARGV[4] = ttl.
    # Returns {allowed (0/1), remaining, retry_after}.
    _LUA_SCRIPT = """
    redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
    local count = redis.call('ZCARD', KEYS[1])
    local limit = tonumber(ARGV[3])
    if count >= limit then
        local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
        local retry = 0
        if #oldest > 0 then
            retry = 60.0 - (tonumber(ARGV[2]) - tonumber(oldest[2]))
            if retry < 0 then retry = 0 end
        end
        return {0, 0, tostring(retry)}
    end
    redis.call('ZADD', KEYS[1], ARGV[2], ARGV[2] .. ':' .. math.random(1000000))
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[4]))
    local remaining = limit - count - 1
    return {1, remaining, '0'}
    """

    def __init__(self) -> None:
        self._windows: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._redis: Any | None = None
        self._lua_sha: str | None = None
        self._redis_failed = False
        self._init_redis()

    def _init_redis(self) -> None:
        """Try to connect to Redis if configured."""
        try:
            redis_url = settings.redis_url
            if redis_url:
                import redis as redis_lib
                self._redis = redis_lib.from_url(
                    redis_url, decode_responses=True, socket_connect_timeout=2
                )
                self._redis.ping()
                self._lua_sha = self._redis.script_load(self._LUA_SCRIPT)
        except Exception:
            # Redis not available — fall back to in-memory silently.
            self._redis = None
            self._lua_sha = None

    def check(self, key: str, limit: int, now: float | None = None) -> tuple[bool, float]:
        """Record one request; return (allowed, retry_after_seconds)."""
        now = now if now is not None else time.time()

        # Try Redis first
        if self._redis is not None and self._lua_sha is not None and not self._redis_failed:
            try:
                result = self._redis.evalsha(
                    self._lua_sha,
                    1,
                    f"rl:{key}",
                    str(now - 60.0),
                    str(now),
                    str(limit),
                    "90",  # TTL: 90s > window to avoid premature eviction
                )
                allowed = int(result[0]) == 1
                retry_after = float(result[2])
                return allowed, retry_after
            except Exception:
                # Redis went away mid-flight — degrade gracefully to in-memory.
                self._redis_failed = True

        # In-memory fallback
        with self._lock:
            window = self._windows.setdefault(key, deque())
            while window and window[0] <= now - 60.0:
                window.popleft()
            if len(window) >= limit:
                retry_after = max(0.0, 60.0 - (now - window[0])) if window else 0.0
                return False, retry_after
            window.append(now)
            return True, 0.0

    def remaining(self, key: str, limit: int, now: float | None = None) -> int:
        now = now if now is not None else time.time()

        # Try Redis first
        if self._redis is not None and not self._redis_failed:
            try:
                self._redis.zremrangebyscore(f"rl:{key}", "-inf", str(now - 60.0))
                count = self._redis.zcard(f"rl:{key}")
                return max(0, limit - count)
            except Exception:
                self._redis_failed = True

        # In-memory fallback
        with self._lock:
            window = self._windows.get(key)
            if not window:
                return limit
            while window and window[0] <= now - 60.0:
                window.popleft()
            return max(0, limit - len(window))


class RateLimitMiddleware:
    """Sliding-window rate limit per API key (default 30/min from settings).

    Exempt: OPTIONS preflight, ``GET /api/v1/health``, the SSE stream endpoint
    (long-polling), and requests without an ``X-API-Key`` header (public routes).
    """

    def __init__(self, app: Any, limit_per_minute: int | None = None) -> None:
        self.app = app
        self.limit_per_minute = limit_per_minute or settings.rate_limit_per_minute
        self._store = _SlidingWindowStore()

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = _scope_headers(scope)
        api_key = headers.get("x-api-key") or ""
        path = scope.get("path", "")
        method = scope.get("method", "GET")
        if method == "OPTIONS" or path == "/api/v1/health" or path.endswith("/events/stream"):
            await self.app(scope, receive, send)
            return

        now = time.time()
        # Keyless traffic is rate-limited by client IP so it can never bypass
        # the limiter (review hardening).
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        if api_key:
            key_hash = hash_api_key(api_key)
        else:
            key_hash = f"ip:{client_ip}"
        allowed, retry_after = self._store.check(key_hash, self.limit_per_minute, now)
        remaining = self._store.remaining(key_hash, self.limit_per_minute, now)
        if not allowed:
            request_id = scope.get("state", {}).get("request_id") or uuid.uuid4().hex
            payload = error_response(
                request_id,
                "rate_limit_exceeded",
                "Rate limit exceeded",
                {"retry_after_seconds": round(retry_after, 2)},
            )
            response = JSONResponse(
                status_code=429,
                content=payload,
                headers={
                    "Retry-After": str(int(math.ceil(retry_after))),
                    "X-Request-Id": request_id,
                    "X-RateLimit-Limit": str(self.limit_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
            )
            await response(scope, receive, send)
            return

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers.setdefault("X-RateLimit-Limit", str(self.limit_per_minute))
                response_headers.setdefault("X-RateLimit-Remaining", str(remaining))
            await send(message)

        await self.app(scope, receive, send_wrapper)


def setup_middleware(app: Any) -> None:
    """Register CORS, rate limiting, and request-context middleware.

    Insertion order matters: RequestContext must be outermost among user
    middleware so ``scope["state"]["request_id"]`` exists before rate limiting.
    """
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.rate_limit_per_minute)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )
