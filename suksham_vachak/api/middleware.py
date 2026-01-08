"""FastAPI middleware for logging and request tracing."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from suksham_vachak.logging import get_logger, set_correlation_id

logger = get_logger(__name__)

# Type alias for middleware call_next function
RequestResponseCallable = Callable[[Request], Awaitable[Response]]


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation IDs to all requests.

    Sets a correlation ID from the X-Correlation-ID header if present,
    otherwise generates a new one. The ID is available via get_correlation_id()
    and included in all log entries within the request context.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseCallable) -> Response:
        """Process request with correlation ID."""
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid4())[:8]  # Short ID for readability

        # Set in context variable for logging
        set_correlation_id(correlation_id)

        # Add to request state for access in routes
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests with timing and status."""

    async def dispatch(self, request: Request, call_next: RequestResponseCallable) -> Response:
        """Log request details."""
        start_time = time.perf_counter()

        # Log request start
        log = logger.bind(
            method=request.method,
            path=request.url.path,
            query=str(request.query_params) if request.query_params else None,
        )

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log based on status code
            if response.status_code >= 500:
                log.error(
                    "Request failed",
                    status=response.status_code,
                    duration_ms=round(duration_ms, 2),
                )
            elif response.status_code >= 400:
                log.warning(
                    "Request client error",
                    status=response.status_code,
                    duration_ms=round(duration_ms, 2),
                )
            else:
                log.info(
                    "Request completed",
                    status=response.status_code,
                    duration_ms=round(duration_ms, 2),
                )

            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log.exception(
                "Request exception",
                error=str(e),
                duration_ms=round(duration_ms, 2),
            )
            raise
