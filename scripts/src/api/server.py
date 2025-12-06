"""FastAPI server for the pipeline API."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .dependencies import set_orchestrator
from .routes import router
from ..pipeline import PipelineOrchestrator
from ..utils.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting pipeline API...")
    orchestrator = PipelineOrchestrator()
    await orchestrator.initialize()
    set_orchestrator(orchestrator)
    logger.info("Pipeline API started")

    yield

    # Shutdown
    logger.info("Shutting down pipeline API...")
    await orchestrator.shutdown()
    logger.info("Pipeline API shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Guide Pipeline API",
        description="API for converting documents to HTML guides",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(router, prefix="/api")

    return app


# Create app instance
app = create_app()
