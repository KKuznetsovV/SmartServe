"""Seed demo tenants for local development. Idempotent.

Run: python -m app.db.seed [--with-second-tenant]
"""

from __future__ import annotations

import argparse
import asyncio

import structlog
from smartserve_shared.security import hash_password
from sqlalchemy import select

from app.db.models import Business, Location, User
from app.db.session import AsyncSessionLocal

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
        existing = await db.execute(select(User).where(User.email == email))
        user = existing.scalar_one_or_none()
        if user:
            return user
    user = User(
        business_id=business_id,
        email=email,
        name=name,
        role=role,
        password_hash=hash_password(password) if password else None,
        pin_hash=hash_password(pin) if pin else None,
    )
    db.add(user)
    return user


async def seed(*, with_second_tenant: bool = False) -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == DEMO_EMAIL))
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
        else:
            logger.info("demo tenant already present, skipping")

        if with_second_tenant:
            other = await db.execute(select(User).where(User.email == OTHER_EMAIL))
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
