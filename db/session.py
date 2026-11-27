"""Database engine and session factory.

The web app creates these once at startup (in its lifespan function) and the worker does the
same in its startup hook. Nothing is created at import time.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str) -> AsyncEngine:
    """Create the async engine (the connection pool) for the given database URL."""
    return create_async_engine(database_url)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return a factory that opens a database session on the given engine."""
    return async_sessionmaker(engine, expire_on_commit=False)
