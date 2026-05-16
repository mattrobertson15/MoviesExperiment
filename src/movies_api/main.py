from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from prometheus_client import make_asgi_app

from .config import Config, parse_config
from .logging_config import setup_logging
from .metrics import ACTORS_TOTAL, MOVIES_TOTAL
from .middleware import LoggingMiddleware, MetricsMiddleware
from .routes import actors, genres, health, movies, version
from .store import Store

logger = logging.getLogger(__name__)


def create_app(config: Config | None = None) -> FastAPI:
    if config is None:
        # When invoked as a uvicorn factory, sys.argv belongs to uvicorn.
        # Read configuration from env vars only (args=[]).
        config = parse_config(args=[])

    setup_logging(config.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.ready = False
        store = Store()
        store.load(config.data_dir)
        app.state.store = store
        app.state.version = config.version
        MOVIES_TOTAL.set(len(store.movies))
        ACTORS_TOTAL.set(len(store.actors))
        app.state.ready = True
        logger.info(
            "Startup complete",
            extra={
                "version": config.version,
                "port": config.port,
                "data_dir": config.data_dir,
                "log_level": config.log_level,
            },
        )
        yield
        logger.info("Shutting down")

    app = FastAPI(
        title="Movies API",
        description="Read-only catalog of movies and actors.",
        version=config.version,
        docs_url="/swagger",
        openapi_url="/swagger/v1/swagger.json",
        redoc_url=None,
        lifespan=lifespan,
    )

    # Prometheus exposition on /metrics (bypasses FastAPI middleware)
    metrics_asgi = make_asgi_app()
    app.mount("/metrics", metrics_asgi)

    # Middleware (order matters: added last = outermost)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(MetricsMiddleware)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        # Spec §6 requires HTTP 400 for all validation violations.
        return JSONResponse(status_code=400, content={"detail": exc.errors()})

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/swagger", status_code=302)

    app.include_router(health.router)
    app.include_router(version.router)
    app.include_router(movies.router, prefix="/api")
    app.include_router(actors.router, prefix="/api")
    app.include_router(genres.router, prefix="/api")

    return app


def main() -> None:
    import uvicorn

    config = parse_config()
    setup_logging(config.log_level)
    app = create_app(config)
    uvicorn.run(app, host="0.0.0.0", port=config.port, log_config=None)


if __name__ == "__main__":
    main()
