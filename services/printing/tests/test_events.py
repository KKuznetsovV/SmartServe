"""Tests for the `order.item_fired` consumer handler and the new `PrintJob` audit trail."""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base, Printer, PrinterRoute, PrintJob
from app.modules.printing.events import handle_order_item_fired


@pytest_asyncio.fixture
async def events_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_handle_order_item_fired_creates_print_job_for_routed_printer(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        printer = Printer(location_id="loc-1", name="Kitchen", type="kitchen")
        session.add(printer)
        await session.flush()
        route = PrinterRoute(printer_id=printer.id, item_id="menu-item-1")
        session.add(route)
        await session.commit()
        printer_id = printer.id

    async with session_factory() as session:
        await handle_order_item_fired(
            "order.item_fired",
            {"orderId": "order-1", "itemId": "item-1", "menuItemId": "menu-item-1", "locationId": "loc-1"},
            session,
        )
        await session.commit()

    async with session_factory() as session:
        result = await session.execute(select(PrintJob))
        jobs = list(result.scalars().all())
        assert len(jobs) == 1
        assert jobs[0].order_id == "order-1"
        assert jobs[0].item_id == "item-1"
        assert jobs[0].printer_id == printer_id


@pytest.mark.asyncio
async def test_handle_order_item_fired_no_routes_is_noop(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        await handle_order_item_fired(
            "order.item_fired",
            {"orderId": "order-1", "itemId": "item-1", "menuItemId": "menu-item-unrouted", "locationId": "loc-1"},
            session,
        )
        await session.commit()

    async with session_factory() as session:
        result = await session.execute(select(PrintJob))
        assert list(result.scalars().all()) == []


@pytest.mark.asyncio
async def test_handle_order_item_fired_missing_fields_is_noop(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        await handle_order_item_fired("order.item_fired", {"orderId": "order-1"}, session)
        await session.commit()

    async with session_factory() as session:
        result = await session.execute(select(PrintJob))
        assert list(result.scalars().all()) == []
