"""Rate limiter middleware for FastAPI.

Provides a simple in-memory rate limiter based on client IP address.
Uses a sliding window counter approach.
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

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean old entries outside the window
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
