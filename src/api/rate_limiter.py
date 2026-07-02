"""Rate limiter middleware for FastAPI.

Provides a simple in-memory rate limiter based on client IP address.
Uses a sliding window counter approach with periodic cleanup.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from utils.logger import setup_logger

logger = setup_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window counter.

    Args:
        max_requests: Maximum requests per window.
        window_seconds: Time window in seconds.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Cleanup every 5 minutes

    def _cleanup_stale_entries(self) -> None:
        """Remove entries for IPs that haven't sent requests recently."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        stale_threshold = now - (self.window_seconds * 2)
        stale_ips = [
            ip for ip, timestamps in self._requests.items()
            if not timestamps or max(timestamps) < stale_threshold
        ]
        for ip in stale_ips:
            del self._requests[ip]

        if stale_ips:
            logger.debug("Cleaned up %d stale rate limit entries", len(stale_ips))

        self._last_cleanup = now

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Periodic cleanup of stale entries
        self._cleanup_stale_entries()

        # Clean old entries outside the window for this IP
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if now - t < self.window_seconds
        ]

        if len(self._requests[client_ip]) >= self.max_requests:
            logger.warning(
                "Rate limit exceeded for %s: %d requests in %ds",
                client_ip,
                len(self._requests[client_ip]),
                self.window_seconds,
            )
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later.",
            )

        self._requests[client_ip].append(now)
        return await call_next(request)


class LoginRateLimiter:
    """Stricter rate limiter for login endpoints.

    Limits login attempts per IP to prevent brute force attacks.
    Uses a sliding window counter approach.
    """

    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def check(self, client_ip: str) -> bool:
        """Check if login attempt is allowed. Returns True if allowed, False if rate limited."""
        now = time.time()

        # Clean old entries outside the window
        self._attempts[client_ip] = [
            t for t in self._attempts[client_ip] if now - t < self.window_seconds
        ]

        if len(self._attempts[client_ip]) >= self.max_attempts:
            logger.warning(
                "Login rate limit exceeded for %s: %d attempts in %ds",
                client_ip,
                len(self._attempts[client_ip]),
                self.window_seconds,
            )
            return False

        self._attempts[client_ip].append(now)
        return True


# Global login rate limiter instance
login_rate_limiter = LoginRateLimiter(max_attempts=5, window_seconds=60)
