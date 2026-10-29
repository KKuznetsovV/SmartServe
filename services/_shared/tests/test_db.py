from __future__ import annotations

import inspect

import pytest
from fastapi import Depends
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from smartserve_shared.db import Base, make_db_session, make_engine, make_get_db, make_sessionmaker

PG_URL = "postgresql+asyncpg://smartserve:smartserve@localhost/smartserve"


def test_fastapi_depends_supports_scope() -> None:
    assert "scope" in inspect.signature(Depends).parameters


def test_make_db_session_uses_function_scope() -> None:
    alias = make_db_session(lambda: None)
    dep = alias.__metadata__[0]
    assert dep.scope == "function"


class _Row(Base):
    __tablename__ = "shared_db_rows"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)


def _pool(engine):  # noqa: ANN001
    return engine.sync_engine.pool


def test_make_engine_defaults_fit_under_postgres_max_connections(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.delenv("DB_POOL_SIZE", raising=False)
    monkeypatch.delenv("DB_MAX_OVERFLOW", raising=False)
    engine = make_engine(PG_URL)
    pool = _pool(engine)
    assert pool.size() == 5
    assert pool._max_overflow == 5
    # Seven services × (pool + overflow) must stay under Postgres' default max_connections=100.
    assert 7 * (pool.size() + pool._max_overflow) < 100


def test_make_engine_reads_pool_env(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("DB_POOL_SIZE", "3")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "2")
    engine = make_engine(PG_URL)
    pool = _pool(engine)
    assert pool.size() == 3
    assert pool._max_overflow == 2


def test_make_engine_explicit_args_override_env(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("DB_POOL_SIZE", "3")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "2")
    engine = make_engine(PG_URL, pool_size=7, max_overflow=1)
    pool = _pool(engine)
    assert pool.size() == 7
    assert pool._max_overflow == 1


async def test_get_db_commits_on_success() -> None:
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    session_factory = make_sessionmaker(engine)
    get_db = make_get_db(session_factory)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async for session in get_db():
        session.add(_Row(id="1", name="ok"))

    async with session_factory() as check:
        found = (await check.execute(select(_Row).where(_Row.id == "1"))).scalar_one()
        assert found.name == "ok"
    await engine.dispose()


async def test_get_db_resolves_sessionmaker_per_request() -> None:
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    factory = make_sessionmaker(engine)
    get_db = make_get_db(lambda: factory)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async for session in get_db():
        session.add(_Row(id="late", name="bound"))

    async with factory() as check:
        found = (await check.execute(select(_Row).where(_Row.id == "late"))).scalar_one()
        assert found.name == "bound"
    await engine.dispose()


async def test_get_db_rolls_back_on_error() -> None:
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    session_factory = make_sessionmaker(engine)
    get_db = make_get_db(session_factory)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    with pytest.raises(RuntimeError):
        async for session in get_db():
            session.add(_Row(id="1", name="nope"))
            raise RuntimeError("boom")

    async with session_factory() as check:
        found = (await check.execute(select(_Row))).scalars().all()
        assert found == []
    await engine.dispose()
