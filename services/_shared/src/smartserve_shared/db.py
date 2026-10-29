"""SQLAlchemy async engine/session helpers with commit-on-success get_db."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def make_engine(
    url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    *,
    echo: bool = False,
    **kwargs: Any,
) -> AsyncEngine:
    options: dict[str, Any] = {"echo": echo, **kwargs}
    if url.startswith("sqlite") or "+aiosqlite" in url:
        return create_async_engine(url, **options)
    options.setdefault("pool_pre_ping", True)
    options["pool_size"] = pool_size
    options["max_overflow"] = max_overflow
    return create_async_engine(url, **options)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


def make_get_db(
    session_factory: async_sessionmaker[AsyncSession],
):
    async def get_db() -> AsyncGenerator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return get_db
