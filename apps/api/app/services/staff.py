from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.db.models import User
from app.schemas.staff import StaffCreate, StaffUpdate


class StaffService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _pin_in_use(self, business_id: str, pin: str, exclude_user_id: str | None = None) -> bool:
        # bcrypt hashes are salted, so uniqueness can't be checked via a SQL query —
        # verify the candidate PIN against every existing hash in the business instead.
        result = await self.db.execute(
            select(User).where(User.business_id == business_id, User.active, User.pin_hash.is_not(None))
        )
        for user in result.scalars().all():
            if user.id == exclude_user_id:
                continue
            if user.pin_hash and verify_password(pin, user.pin_hash):
                return True
        return False

    async def list_staff(self, business_id: str) -> list[User]:
        result = await self.db.execute(select(User).where(User.business_id == business_id))
        return list(result.scalars().all())

    async def get_user(self, user_id: str) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def create_staff(self, business_id: str, data: StaffCreate) -> User:
        if data.email:
            existing = await self.db.execute(select(User).where(User.email == data.email))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        if data.pin and await self._pin_in_use(business_id, data.pin):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="PIN already in use by another staff member"
            )

        user = User(
            business_id=business_id,
            email=data.email,
            name=data.name,
            role=data.role,
            language=data.language,
            password_hash=hash_password(data.password) if data.password else None,
            pin_hash=hash_password(data.pin) if data.pin else None,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update_staff(self, user_id: str, data: StaffUpdate) -> User:
        user = await self.get_user(user_id)
        updates = data.model_dump(exclude_none=True)
        if "pin" in updates:
            pin = updates.pop("pin")
            if await self._pin_in_use(user.business_id, pin, exclude_user_id=user.id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="PIN already in use by another staff member"
                )
            user.pin_hash = hash_password(pin)
        for field, value in updates.items():
            setattr(user, field, value)
        await self.db.flush()
        return user
