from __future__ import annotations

import logging
import re
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .metrics import REQUEST_COUNT, REQUEST_LATENCY

logger = logging.getLogger(__name__)

# IDs in path that should be normalized to template placeholders
_MOVIE_ID_RE = re.compile(r"/tt\d{5,9}")
_ACTOR_ID_RE = re.compile(r"/nm\d{5,9}")


def _normalize_path(path: str) -> str:
    path = _MOVIE_ID_RE.sub("/{movie_id}", path)
    path = _ACTOR_ID_RE.sub("/{actor_id}", path)
    return path


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        # Prefer FastAPI's resolved route path (avoids high cardinality from IDs)
        route = request.scope.get("route")
        path = route.path if route else _normalize_path(request.url.path)

        REQUEST_LATENCY.labels(method=request.method, path=path).observe(duration)
        REQUEST_COUNT.labels(
            method=request.method,
            path=path,
            status_code=str(response.status_code),
        ).inc()
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query) or None,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response
