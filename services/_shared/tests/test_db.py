from __future__ import annotations

import pytest
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from smartserve_shared.db import Base, make_engine, make_get_db, make_sessionmaker


class _Row(Base):
    __tablename__ = "shared_db_rows"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)


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
