import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.modules.health.controllers import router as health_router

# Fails fast with a clear validation error if a required setting is missing.
settings = get_settings()

logging.basicConfig(level=logging.INFO if settings.is_production else logging.DEBUG)


def create_app() -> FastAPI:
    app = FastAPI(
        title="BariBhara API",
        description="Rent, flat, tenant and maintenance management for small Dhaka landlords.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
