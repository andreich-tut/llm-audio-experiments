"""
FastAPI application factory for the Telegram Mini App API.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infrastructure.database.database import get_db
from interfaces.webapp.routes import oauth, settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_db()
    await db.init_db()
    logger.info("Mini App API started")
    yield
    await db.close()
    logger.info("Mini App API stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="TG Bot Mini App API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Tighten via CORS_ORIGINS env var in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(settings.router, prefix="/api/v1")
    app.include_router(oauth.router, prefix="/api/v1")

    return app


app = create_app()
