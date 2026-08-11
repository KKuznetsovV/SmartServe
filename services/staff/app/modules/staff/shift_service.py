"""Shift service — open/close cash-drawer shifts per location."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Shift
from app.modules.staff.shift_schemas import ShiftClose, ShiftOpen


class ShiftService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def open_shift(self, user_id: str, location_id: str, data: ShiftOpen) -> Shift:
        existing = await self.db.execute(select(Shift).where(Shift.location_id == location_id, Shift.status == "open"))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="A shift is already open for this location")

        shift = Shift(
            location_id=location_id,
            opened_by=user_id,
            opening_cash=data.opening_cash,
            notes=data.notes,
            status="open",
        )
        self.db.add(shift)
        await self.db.flush()
        return shift

    async def close_shift(self, shift_id: str, user_id: str, data: ShiftClose) -> Shift:
        result = await self.db.execute(select(Shift).where(Shift.id == shift_id))
        shift = result.scalar_one_or_none()
        if not shift:
            raise HTTPException(status_code=404, detail="Shift not found")
        if shift.status != "open":
            raise HTTPException(status_code=400, detail="Shift is already closed")

        shift.closed_by = user_id
        shift.closed_at = datetime.now(UTC)
        shift.closing_cash = data.closing_cash
        shift.status = "closed"
        if data.notes:
            shift.notes = data.notes
        await self.db.flush()
        return shift

    async def get_current(self, location_id: str) -> Shift | None:
        result = await self.db.execute(select(Shift).where(Shift.location_id == location_id, Shift.status == "open"))
        return result.scalar_one_or_none()

    async def list_shifts(self, location_id: str, limit: int = 30) -> list[Shift]:
        result = await self.db.execute(
            select(Shift).where(Shift.location_id == location_id).order_by(Shift.opened_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
