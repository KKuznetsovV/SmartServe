from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from smartserve_shared.db import Base, make_engine, make_sessionmaker
from smartserve_shared.tenancy import verify_location_owned


class _Location(Base):
    __tablename__ = "tenancy_locations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    business_id: Mapped[str] = mapped_column(String)


@pytest.mark.parametrize(
    ("location_id", "business_id", "ok"),
    [
        ("loc-a", "biz-a", True),
        ("loc-a", "biz-b", False),
        ("missing", "biz-a", False),
    ],
)
async def test_verify_location_owned(
    location_id: str, business_id: str, ok: bool
) -> None:
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    factory = make_sessionmaker(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as db:
        db.add(_Location(id="loc-a", business_id="biz-a"))
        await db.flush()
        if ok:
            loc = await verify_location_owned(db, location_id, business_id, _Location)
            assert loc.id == "loc-a"
        else:
            with pytest.raises(HTTPException) as exc:
                await verify_location_owned(db, location_id, business_id, _Location)
            assert exc.value.status_code == 404
    await engine.dispose()
