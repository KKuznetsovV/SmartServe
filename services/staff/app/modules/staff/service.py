from fastapi import HTTPException, status
from smartserve_shared.roles import can_assign_role, can_manage_user
from smartserve_shared.security import hash_password
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.modules.staff.schemas import StaffCreate, StaffUpdate


class StaffService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_staff(self, business_id: str) -> list[User]:
        result = await self.db.execute(select(User).where(User.business_id == business_id))
        return list(result.scalars().all())

    async def get_user(self, user_id: str, business_id: str | None = None) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        # A manager must only ever reach staff within their OWN business — never trust the
        # path param alone (a cleverly-guessed user_id from another business must 404, not leak).
        if not user or (business_id is not None and user.business_id != business_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def create_staff(self, actor: User, data: StaffCreate) -> User:
        if not can_assign_role(actor.role, data.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create a user with that role",
            )
        if data.email:
            existing = await self.db.execute(select(User).where(func.lower(User.email) == data.email))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

        user = User(
            business_id=actor.business_id,
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

    async def update_staff(self, actor: User, user_id: str, data: StaffUpdate) -> User:
        user = await self.get_user(user_id, actor.business_id)
        updates = data.model_dump(exclude_unset=True)
        if updates.get("role") == user.role:
            updates.pop("role")
        if "active" in updates and updates["active"] is user.active:
            updates.pop("active")

        changing_role = "role" in updates
        changing_active = "active" in updates
        if (changing_role or changing_active) and user.id == actor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot change your own role or deactivate yourself",
            )

        if user.id != actor.id and not can_manage_user(actor.role, user.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update a user at or above your role",
            )

        if changing_role and not can_assign_role(actor.role, updates["role"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot assign that role",
            )

        losing_active_owner = (
            user.role == "owner"
            and user.active
            and ((changing_role and updates["role"] != "owner") or (changing_active and updates["active"] is False))
        )
        if losing_active_owner:
            await self._assert_not_last_owner(user)

        if "pin" in updates:
            pin = updates.pop("pin")
            user.pin_hash = hash_password(pin) if pin else None
        for field, value in updates.items():
            setattr(user, field, value)
        await self.db.flush()
        return user

    async def _assert_not_last_owner(self, user: User) -> None:
        result = await self.db.execute(
            select(func.count())
            .select_from(User)
            .where(User.business_id == user.business_id, User.role == "owner", User.active.is_(True))
        )
        if int(result.scalar_one()) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate or demote the last owner",
            )
