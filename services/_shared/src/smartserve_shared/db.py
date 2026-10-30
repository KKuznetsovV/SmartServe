"""SQLAlchemy async engine/session helpers with commit-on-success get_db."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Callable
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from smartserve_shared import mirrors as _mirrors  # noqa: F401 — register before_flush

DEFAULT_POOL_SIZE = 5
DEFAULT_MAX_OVERFLOW = 5


class Base(DeclarativeBase):
    pass


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def make_engine(
    url: str,
    pool_size: int | None = None,
    max_overflow: int | None = None,
    *,
    echo: bool = False,
    **kwargs: Any,
) -> AsyncEngine:
    """Create an async engine.

    Pool size comes from `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` (defaults 5 / 5) so seven
    services stay under Postgres' default `max_connections` of 100. Explicit arguments
    override the environment.
    """
    options: dict[str, Any] = {"echo": echo, **kwargs}
    if url.startswith("sqlite") or "+aiosqlite" in url:
        return create_async_engine(url, **options)
    if pool_size is None:
        pool_size = _env_int("DB_POOL_SIZE", DEFAULT_POOL_SIZE)
    if max_overflow is None:
        max_overflow = _env_int("DB_MAX_OVERFLOW", DEFAULT_MAX_OVERFLOW)
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
    session_factory: async_sessionmaker[AsyncSession] | Callable[[], async_sessionmaker[AsyncSession]],
):
    """Build a FastAPI `get_db` dependency.

    Pass an `async_sessionmaker` or a zero-arg getter that returns one. A getter
    is required when tests monkeypatch `AsyncSessionLocal` on the service module:
    the factory is resolved per request, not captured at import.
    """

    def _factory() -> async_sessionmaker[AsyncSession]:
        if isinstance(session_factory, async_sessionmaker):
            return session_factory
        return session_factory()

    async def get_db() -> AsyncGenerator[AsyncSession]:
        async with _factory()() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return get_db


def make_db_session(get_db: Callable[..., Any]) -> Any:
    """`DbSession` alias: commit/rollback run before the response is sent.

    FastAPI's default yield-dependency scope finishes *after* the response, which
    is how a 2xx could leave the client before `commit()` failed. `scope="function"`
    runs teardown around the path operation instead.
    """
    return Annotated[AsyncSession, Depends(get_db, scope="function")]
