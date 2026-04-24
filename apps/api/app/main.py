from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()
    settings.validate_runtime()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="StudyPilot API",
        version="0.1.0",
        summary="Phase 1 backend core loop for StudyPilot",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(application)
    application.include_router(api_router, prefix="/api")

    @application.get("/healthz", tags=["health"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/readyz", tags=["health"])
    def readyz() -> dict[str, str]:
        return {"status": "ready"}

    return application


app = create_app()
