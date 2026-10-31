"""Authentication business logic: credential/PIN verification and token issuance."""

import uuid
from typing import Any, NoReturn

from fastapi import HTTPException, status
from smartserve_shared.lockout import (
    clear_failures,
    email_ident,
    emit_lockout,
    pin_ident,
    raise_if_locked,
    raise_now_locked,
    record_failure,
)
from smartserve_shared.security import (
    access_expire_seconds,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Location, Outbox, User
from app.modules.auth.refresh_store import register as register_refresh
from app.modules.auth.refresh_store import rotate as rotate_refresh
from app.modules.auth.schemas import TokenResponse


class AuthService:
    def __init__(self, db: AsyncSession, redis: Any | None = None):
        self.db = db
        self.redis = redis

    def _lockout_window(self) -> tuple[int, int]:
        return settings.MAX_PIN_ATTEMPTS, settings.PIN_LOCKOUT_MINUTES * 60

    async def _fail(
        self,
        ident: str,
        *,
        detail: str,
        user: User | None = None,
        device_id: str | None = None,
    ) -> NoReturn:
        max_failures, lockout_seconds = self._lockout_window()
        retry_after = await record_failure(
            self.redis, ident, max_failures=max_failures, lockout_seconds=lockout_seconds
        )
        if retry_after is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
        if user is not None:
            await emit_lockout(
                self.db,
                Outbox,
                business_id=user.business_id,
                user_id=user.id,
                device_id=device_id,
            )
        await raise_now_locked(self.db, retry_after)

    async def login(self, email: str, password: str) -> tuple[TokenResponse, str]:
        ident = email_ident(email)
        await raise_if_locked(self.redis, ident)
        result = await self.db.execute(select(User).where(func.lower(User.email) == email.lower(), User.active))
        user = result.scalar_one_or_none()
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            await self._fail(ident, detail="Invalid credentials", user=user)
        await clear_failures(self.redis, ident)
        return await self._issue_tokens(user)

    async def list_pin_staff(self, location_id: str) -> list[User]:
        loc_result = await self.db.execute(select(Location).where(Location.id == location_id, Location.active))
        location = loc_result.scalar_one_or_none()
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
        result = await self.db.execute(
            select(User)
            .where(User.business_id == location.business_id, User.active, User.pin_hash.is_not(None))
            .order_by(User.name)
        )
        return list(result.scalars().all())

    async def pin_login(
        self, location_id: str, user_id: str, pin: str, *, device_id: str | None = None
    ) -> tuple[TokenResponse, str]:
        # Duplicate PINs across staff are allowed (business owner's choice), so the caller
        # must identify which user they're authenticating as (picked via the staff list) —
        # we only verify the PIN against that specific user's hash, never brute-force match.
        ident = pin_ident(user_id, device_id)
        await raise_if_locked(self.redis, ident)
        loc_result = await self.db.execute(select(Location).where(Location.id == location_id, Location.active))
        location = loc_result.scalar_one_or_none()
        if not location:
            await self._fail(ident, detail="Invalid PIN", device_id=device_id)

        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.business_id == location.business_id,
                User.active,
                User.pin_hash.is_not(None),
            )
        )
        user = result.scalar_one_or_none()
        if not user or not user.pin_hash or not verify_password(pin, user.pin_hash):
            await self._fail(ident, detail="Invalid PIN", user=user, device_id=device_id)
        await clear_failures(self.redis, ident)
        return await self._issue_tokens(user)

    async def verify_manager_pin(
        self, location_id: str, manager_user_id: str, pin: str, *, device_id: str | None = None
    ) -> User:
        """Confirm a manager/owner override (e.g. deleting a submitted order item) without
        switching the current session — verifies the given user is a manager/owner at this
        location and that the PIN matches, but issues no tokens."""
        ident = pin_ident(manager_user_id, device_id)
        await raise_if_locked(self.redis, ident)
        loc_result = await self.db.execute(select(Location).where(Location.id == location_id, Location.active))
        location = loc_result.scalar_one_or_none()
        if not location:
            await self._fail(ident, detail="Invalid manager PIN", device_id=device_id)

        result = await self.db.execute(
            select(User).where(
                User.id == manager_user_id,
                User.business_id == location.business_id,
                User.role.in_(["owner", "manager"]),
                User.active,
                User.pin_hash.is_not(None),
            )
        )
        user = result.scalar_one_or_none()
        if not user or not user.pin_hash or not verify_password(pin, user.pin_hash):
            await self._fail(ident, detail="Invalid manager PIN", user=user, device_id=device_id)
        await clear_failures(self.redis, ident)
        return user

    async def refresh(self, refresh_token: str) -> tuple[TokenResponse, str]:
        payload = decode_token(refresh_token, expected_type="refresh")
        jti = payload.get("jti")
        family_id = payload.get("fam")
        if not jti or not family_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
        # Reload the user so refreshed tokens keep claims and deactivated users are rejected
        result = await self.db.execute(select(User).where(User.id == payload["sub"], User.active))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")
        new_jti = str(uuid.uuid4())
        await rotate_refresh(self.redis, presented_jti=jti, family_id=family_id, new_jti=new_jti)
        return await self._issue_tokens(user, family_id=family_id, jti=new_jti)

    async def get_user_profile(self, token: str) -> dict:
        payload = decode_token(token)
        result = await self.db.execute(select(User).where(User.id == payload["sub"], User.active))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "businessId": user.business_id,
            "language": user.language,
            "active": user.active,
        }

    async def _issue_tokens(
        self, user: User, *, family_id: str | None = None, jti: str | None = None
    ) -> tuple[TokenResponse, str]:
        extra = {"business_id": user.business_id, "role": user.role}
        refresh = create_refresh_token(user.id, family_id=family_id, jti=jti)
        refresh_payload = decode_token(refresh, expected_type="refresh")
        await register_refresh(self.redis, family_id=refresh_payload["fam"], jti=refresh_payload["jti"])
        return (
            TokenResponse(
                access_token=create_access_token(user.id, extra),
                expires_in=access_expire_seconds(),
            ),
            refresh,
        )
