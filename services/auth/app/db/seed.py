"""Seed demo tenants for local development. Idempotent.

Run: python -m app.db.seed [--with-second-tenant]
"""

from __future__ import annotations

import argparse
import asyncio
import secrets

import structlog
from smartserve_shared.security import hash_password
from sqlalchemy import func, select

from app.db.models import Business, Device, Location, User
from app.db.session import AsyncSessionLocal
from app.modules.auth.device_service import hash_device_token

logger = structlog.get_logger()

DEMO_EMAIL = "owner@demo.com"
DEMO_PASSWORD = "demo1234"
MANAGER_EMAIL = "manager@demo.com"
MANAGER_PIN = "2222"
WAITER_PIN = "1234"
KITCHEN_PIN = "5678"
OTHER_EMAIL = "owner@other.com"
OTHER_PASSWORD = "other1234"


async def _ensure_user(
    db,
    *,
    business_id: str,
    email: str | None,
    name: str,
    role: str,
    password: str | None = None,
    pin: str | None = None,
) -> User:
    if email:
        existing = await db.execute(select(User).where(func.lower(User.email) == email.lower()))
        user = existing.scalar_one_or_none()
        if user:
            return user
    user = User(
        business_id=business_id,
        email=email.lower() if email else None,
        name=name,
        role=role,
        password_hash=hash_password(password) if password else None,
        pin_hash=hash_password(pin) if pin else None,
    )
    db.add(user)
    return user


async def seed(*, with_second_tenant: bool = False) -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(func.lower(User.email) == DEMO_EMAIL))
        owner = existing.scalar_one_or_none()
        if owner is None:
            biz = Business(name="Demo Restaurant", country="IL", currency="ILS")
            db.add(biz)
            await db.flush()
            loc = Location(business_id=biz.id, name="Main Branch", address="1 Rothschild Blvd, Tel Aviv")
            db.add(loc)
            await db.flush()
            await _ensure_user(
                db,
                business_id=biz.id,
                email=DEMO_EMAIL,
                name="Demo Owner",
                role="owner",
                password=DEMO_PASSWORD,
            )
            await _ensure_user(
                db,
                business_id=biz.id,
                email=MANAGER_EMAIL,
                name="Demo Manager",
                role="manager",
                password=DEMO_PASSWORD,
                pin=MANAGER_PIN,
            )
            await _ensure_user(
                db,
                business_id=biz.id,
                email=None,
                name="Demo Waiter",
                role="waiter",
                pin=WAITER_PIN,
            )
            await _ensure_user(
                db,
                business_id=biz.id,
                email=None,
                name="Demo Cook",
                role="kitchen",
                pin=KITCHEN_PIN,
            )
            logger.info("demo tenant seeded", business_id=biz.id, location_id=loc.id)
            loc_id = loc.id
            creator = (await db.execute(select(User).where(func.lower(User.email) == DEMO_EMAIL))).scalar_one()
            await _ensure_pos_device(db, location_id=loc_id, created_by=creator.id)
        else:
            logger.info("demo tenant already present, skipping")
            existing_loc = (
                (await db.execute(select(Location).where(Location.business_id == owner.business_id))).scalars().first()
            )
            if existing_loc is not None:
                await _ensure_pos_device(db, location_id=existing_loc.id, created_by=owner.id)

        if with_second_tenant:
            other = await db.execute(select(User).where(func.lower(User.email) == OTHER_EMAIL))
            if other.scalar_one_or_none() is None:
                biz = Business(name="Other Restaurant", country="IL", currency="ILS")
                db.add(biz)
                await db.flush()
                loc = Location(business_id=biz.id, name="Other Branch", address="2 Dizengoff St, Tel Aviv")
                db.add(loc)
                await _ensure_user(
                    db,
                    business_id=biz.id,
                    email=OTHER_EMAIL,
                    name="Other Owner",
                    role="owner",
                    password=OTHER_PASSWORD,
                )
                logger.info("second tenant seeded", business_id=biz.id, location_id=loc.id)

        await db.commit()


async def _ensure_pos_device(db, *, location_id: str, created_by: str) -> None:
    existing = await db.execute(
        select(Device).where(Device.location_id == location_id, Device.type == "pos", Device.revoked_at.is_(None))
    )
    if existing.scalar_one_or_none() is not None:
        return
    raw = secrets.token_urlsafe(32)
    db.add(
        Device(
            location_id=location_id,
            name="Demo POS",
            type="pos",
            token_hash=hash_device_token(raw),
            created_by=created_by,
        )
    )
    logger.info("demo POS device registered", location_id=location_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed SmartServe demo tenants.")
    parser.add_argument(
        "--with-second-tenant",
        action="store_true",
        help="Also create owner@other.com for the API test suite.",
    )
    args = parser.parse_args()
    asyncio.run(seed(with_second_tenant=args.with_second_tenant))


if __name__ == "__main__":
    main()
