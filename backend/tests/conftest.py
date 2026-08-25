import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def isolated_async_db(monkeypatch):
    """
    Give each async test a fresh asyncpg engine bound to the current event loop.
    Prevents 'another operation is in progress' / 'different loop' flakes in CI.
    """
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:password@localhost:5432/aijobdb",
    )
    test_engine = create_async_engine(url, poolclass=NullPool, echo=False, future=True)
    test_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    import app.infrastructure.db.session as db_session

    monkeypatch.setattr(db_session, "engine", test_engine, raising=False)
    monkeypatch.setattr(db_session, "async_session", test_session_factory, raising=False)

    yield

    await test_engine.dispose()


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
