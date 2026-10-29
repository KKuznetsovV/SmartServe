"""Demo seed must create the documented logins and stay idempotent."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import seed as seed_mod
from app.db.models import Business, User
from app.db.session import Base


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_seed_creates_demo_users_and_is_idempotent(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(seed_mod, "AsyncSessionLocal", factory)

    await seed_mod.seed()
    await seed_mod.seed()

    async with factory() as db:
        n_biz = (await db.execute(select(func.count()).select_from(Business))).scalar_one()
        assert n_biz == 1
        emails = set((await db.execute(select(User.email).where(User.email.is_not(None)))).scalars().all())
        assert emails == {"owner@demo.com", "manager@demo.com"}
        roles = set((await db.execute(select(User.role))).scalars().all())
        assert roles == {"owner", "manager", "waiter", "kitchen"}

    await seed_mod.seed(with_second_tenant=True)
    async with factory() as db:
        n_biz = (await db.execute(select(func.count()).select_from(Business))).scalar_one()
        assert n_biz == 2
        emails = set((await db.execute(select(User.email).where(User.email.is_not(None)))).scalars().all())
        assert "owner@other.com" in emails

    await seed_mod.seed(with_second_tenant=True)
    async with factory() as db:
        n_biz = (await db.execute(select(func.count()).select_from(Business))).scalar_one()
        assert n_biz == 2

    await engine.dispose()


def test_auth_baseline_has_downgrade():
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / "alembic/versions/0001_baseline.py").read_text(encoding="utf-8")
    for table in ("businesses", "locations", "users"):
        assert table in text
    assert "def downgrade" in text
    env = (Path(__file__).resolve().parents[1] / "alembic/env.py").read_text(encoding="utf-8")
    assert "alembic_version_auth" in env
    assert "include_object" in env
