import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm.exc import StaleDataError

from app.core.body_limit import BodyLimitMiddleware
from app.core.config import Settings, get_settings
from app.core.errors import ServiceError
from app.database.session import Base, create_database
from app.ai.gemini import GeminiAnalyzer
from app.routers import analysis, auth, journal, library, tracking
from app.services.events import RedisEventService
from app.websocket.manager import ConnectionManager
from app.websocket.router import router as websocket_router
from seed.library import seed_library


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.validate()
    engine, session_factory = create_database(settings.database_url)
    manager = ConnectionManager()
    events = RedisEventService(settings.redis_url, manager)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(engine)
        with session_factory() as db:
            seed_library(db)
        await events.start()
        yield
        await events.stop()
        engine.dispose()

    app = FastAPI(title="Grief Copilot API", version="1.0.0",
                  docs_url="/api/docs", redoc_url="/api/redoc",
                  openapi_url="/api/openapi.json", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.manager = manager
    app.state.events = events
    app.state.analyzer = GeminiAnalyzer(settings)
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "DELETE"],
                       allow_headers=["Authorization", "Content-Type"])

    @app.exception_handler(ServiceError)
    async def service_error(request: Request, error: ServiceError):
        headers = {"Retry-After": "60"} if error.status_code == 429 else {}
        return JSONResponse({"detail": error.code}, status_code=error.status_code, headers=headers)

    @app.exception_handler(StaleDataError)
    async def stale_write(request: Request, error: StaleDataError):
        return JSONResponse({"detail": "concurrent_update"}, status_code=409)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        return JSONResponse({"detail": [
            {"loc": list(item["loc"]), "type": item["type"], "msg": item["msg"]}
            for item in error.errors()
        ]}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception):
        logging.getLogger(__name__).error("request_failed", extra={"error_type": type(error).__name__})
        return JSONResponse({"detail": "internal_server_error"}, status_code=500)

    @app.get("/api/healthz", tags=["health"])
    async def health():
        with session_factory() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok", "redis": await events.healthy(),
                "gemini_configured": bool(settings.gemini_key)}

    @app.get("/api", tags=["health"])
    def api_info():
        return {"name": "Grief Copilot API", "docs": "/api/docs",
                "disclaimer": "Emotional support only. Not a substitute for professional health care."}

    app.include_router(auth.router, prefix="/api")
    app.include_router(journal.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(library.router, prefix="/api")
    app.include_router(tracking.router, prefix="/api")
    app.include_router(websocket_router, prefix="/api")
    return app
