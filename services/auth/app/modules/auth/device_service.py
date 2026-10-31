"""Register, list, revoke, and authenticate paired devices."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, Location, User
from app.modules.auth.device_schemas import DEVICE_TYPES, DeviceCreate

_UNAUTHORIZED = "Invalid or missing device token"


def hash_device_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


class DeviceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _owned_location(self, location_id: str, business_id: str) -> Location:
        result = await self.db.execute(select(Location).where(Location.id == location_id))
        location = result.scalar_one_or_none()
        if not location or location.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
        return location

    async def register(self, location_id: str, data: DeviceCreate, actor: User) -> tuple[Device, str]:
        if data.type not in DEVICE_TYPES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid device type")
        await self._owned_location(location_id, actor.business_id)
        raw = secrets.token_urlsafe(32)
        device = Device(
            location_id=location_id,
            name=data.name.strip(),
            type=data.type,
            token_hash=hash_device_token(raw),
            created_by=actor.id,
        )
        if not device.name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Device name is required")
        self.db.add(device)
        await self.db.flush()
        return device, raw

    async def list_for_location(self, location_id: str, actor: User) -> list[Device]:
        await self._owned_location(location_id, actor.business_id)
        result = await self.db.execute(
            select(Device).where(Device.location_id == location_id).order_by(Device.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke(self, device_id: str, actor: User) -> Device:
        result = await self.db.execute(select(Device).where(Device.id == device_id))
        device = result.scalar_one_or_none()
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        await self._owned_location(device.location_id, actor.business_id)
        if device.revoked_at is None:
            device.revoked_at = _now()
            await self.db.flush()
        return device

    async def resolve(self, raw_token: str | None) -> Device:
        if not raw_token or not raw_token.strip():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHORIZED)
        digest = hash_device_token(raw_token.strip())
        result = await self.db.execute(select(Device).where(Device.token_hash == digest))
        device = result.scalar_one_or_none()
        if not device or device.revoked_at is not None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHORIZED)
        device.last_seen_at = _now()
        await self.db.flush()
        return device

    async def authenticate(self, raw_token: str | None, location_id: str) -> Device:
        device = await self.resolve(raw_token)
        if device.location_id != location_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHORIZED)
        return device
