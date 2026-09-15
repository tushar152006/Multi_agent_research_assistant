import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.api.routes.health import router as health_router
from backend.api.routes.research import router as research_router
from backend.api.routes.websocket import router as ws_router
from backend.core.config import get_settings

logger = logging.getLogger("backend.api")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject standard security hardening headers into all HTTP responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Backend API for the Multi-Agent Research Assistant.",
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings.environment.lower() == "production":
        @app.exception_handler(Exception)
        async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
            logger.error("Unhandled server exception on %s: %s", request.url.path, exc, exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "An internal server error occurred. Please contact the administrator."},
            )

    app.include_router(health_router)
    app.include_router(research_router, prefix=settings.api_v1_prefix)
    app.include_router(ws_router)

    return app


app = create_app()

