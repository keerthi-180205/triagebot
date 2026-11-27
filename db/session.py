"""Database engine and session factory.

The web app creates these once at startup (in its lifespan function) and the worker does the
same in its startup hook. Nothing is created at import time.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def create_engine(database_url: str) -> AsyncEngine:
    # TODO: return an async engine for database_url
    raise NotImplementedError


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # TODO: return a sessionmaker bound to the engine with expire_on_commit=False
    # (objects stay readable after commit, which async code needs)
    raise NotImplementedError
