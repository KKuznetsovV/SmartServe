"""Authentication business logic: credential/PIN verification and token issuance."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.db.models import Location, User
from app.schemas.auth import TokenResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def login(self, email: str, password: str) -> TokenResponse:
        result = await self.db.execute(select(User).where(User.email == email, User.active))
        user = result.scalar_one_or_none()
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return self._issue_tokens(user)

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

    async def pin_login(self, location_id: str, user_id: str, pin: str) -> TokenResponse:
        # Duplicate PINs across staff are allowed (business owner's choice), so the caller
        # must identify which user they're authenticating as (picked via the staff list) —
        # we only verify the PIN against that specific user's hash, never brute-force match.
        loc_result = await self.db.execute(select(Location).where(Location.id == location_id, Location.active))
        location = loc_result.scalar_one_or_none()
        if not location:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid PIN")

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
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid PIN")
        return self._issue_tokens(user)

    async def verify_manager_pin(self, location_id: str, manager_user_id: str, pin: str) -> User:
        """Confirm a manager/owner override (e.g. deleting a submitted order item) without
        switching the current session — verifies the given user is a manager/owner at this
        location and that the PIN matches, but issues no tokens."""
        loc_result = await self.db.execute(select(Location).where(Location.id == location_id, Location.active))
        location = loc_result.scalar_one_or_none()
        if not location:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid manager PIN")

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
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid manager PIN")
        return user

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token, expected_type="refresh")
        # Reload the user so refreshed tokens keep claims and deactivated users are rejected
        result = await self.db.execute(select(User).where(User.id == payload["sub"], User.active))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")
        return self._issue_tokens(user)

    async def get_user_profile(self, token: str) -> dict:
        payload = decode_token(token)
        result = await self.db.execute(select(User).where(User.id == payload["sub"]))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "businessId": user.business_id,
            "language": user.language,
        }

    @staticmethod
    def _issue_tokens(user: User) -> TokenResponse:
        extra = {"business_id": user.business_id, "role": user.role}
        return TokenResponse(
            access_token=create_access_token(user.id, extra),
            refresh_token=create_refresh_token(user.id),
            expires_in=900,
        )
