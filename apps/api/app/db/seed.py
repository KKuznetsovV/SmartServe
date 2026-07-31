"""Seed demo data for local development. Idempotent — skips if demo business exists.

Run: python -m app.db.seed
"""

import asyncio

import structlog
from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import (
    Business,
    Location,
    MenuCategory,
    MenuItem,
    Table,
    User,
)
from app.db.session import AsyncSessionLocal

logger = structlog.get_logger()

DEMO_EMAIL = "owner@demo.com"
DEMO_PASSWORD = "demo1234"
WAITER_PIN = "1234"
KITCHEN_PIN = "5678"


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == DEMO_EMAIL))
        if existing.scalar_one_or_none():
            logger.info("Demo data already seeded, skipping")
            return

        biz = Business(name="Demo Restaurant", country="IL", currency="ILS")
        db.add(biz)
        await db.flush()

        loc = Location(business_id=biz.id, name="Main Branch", address="1 Rothschild Blvd, Tel Aviv")
        db.add(loc)
        await db.flush()

        db.add_all(
            [
                User(
                    business_id=biz.id,
                    email=DEMO_EMAIL,
                    name="Demo Owner",
                    role="owner",
                    password_hash=hash_password(DEMO_PASSWORD),
                ),
                User(business_id=biz.id, name="Demo Waiter", role="waiter", pin_hash=hash_password(WAITER_PIN)),
                User(business_id=biz.id, name="Demo Cook", role="kitchen", pin_hash=hash_password(KITCHEN_PIN)),
            ]
        )

        starters = MenuCategory(location_id=loc.id, name="Starters", name_he="ראשונות", sort_order=0)
        mains = MenuCategory(location_id=loc.id, name="Mains", name_he="עיקריות", sort_order=1)
        drinks = MenuCategory(location_id=loc.id, name="Drinks", name_he="שתייה", sort_order=2)
        db.add_all([starters, mains, drinks])
        await db.flush()

        db.add_all(
            [
                MenuItem(category_id=starters.id, name="Hummus", name_he="חומוס", price=28.0),
                MenuItem(category_id=starters.id, name="Falafel Plate", name_he="פלאפל", price=32.0),
                MenuItem(category_id=mains.id, name="Burger", name_he="המבורגר", price=68.0, preparation_time_min=15),
                MenuItem(category_id=mains.id, name="Schnitzel", name_he="שניצל", price=62.0, preparation_time_min=12),
                MenuItem(
                    category_id=mains.id,
                    name="Salmon Fillet",
                    name_he="פילה סלמון",
                    price=94.0,
                    preparation_time_min=18,
                ),
                MenuItem(category_id=drinks.id, name="Cola", name_he="קולה", price=12.0, preparation_time_min=1),
                MenuItem(category_id=drinks.id, name="Lemonade", name_he="לימונדה", price=14.0, preparation_time_min=2),
            ]
        )

        db.add_all([Table(location_id=loc.id, name=f"T{i}", capacity=4) for i in range(1, 9)])

        await db.commit()
        logger.info("Demo data seeded", business_id=biz.id, location_id=loc.id, email=DEMO_EMAIL)


if __name__ == "__main__":
    asyncio.run(seed())
