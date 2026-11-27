"""FastAPI application entry point. Run with: uvicorn app.main:app --reload"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes import health
from common.config import get_settings
from common.logging import setup_logging
from db.session import create_engine, create_session_factory


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open shared resources on startup and close them on shutdown."""
    setup_logging()
    settings = get_settings()
    engine = create_engine(settings.database_url)
    app.state.session_factory = create_session_factory(engine)
    yield
    await engine.dispose()


app = FastAPI(title="TriageBot", lifespan=lifespan)
app.include_router(health.router)
