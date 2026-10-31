"""Tests for the wildcard event consumer: EventLog audit trail + Order mirror projection fix.

This is the real bug fix from the RabbitMQ rollout — reporting's Order/OrderItem mirror
tables were never populated by anything before this event bus existed, so `/reports/summary`
always returned zero rows in real usage. These handlers keep the mirror in sync.
"""

import json

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base, EventLog, ReportingOrder, ReportingOrderItem
from app.modules.reports.events import handle_any_event


@pytest_asyncio.fixture
async def events_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


async def _handle(session_factory, routing_key: str, payload: dict) -> None:
    async with session_factory() as session:
        await handle_any_event(routing_key, payload, session)
        await session.commit()


@pytest.mark.asyncio
async def test_handle_any_event_always_logs_to_event_log(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)

    await _handle(session_factory, "staff.created", {"userId": "u-1", "role": "waiter"})

    async with session_factory() as session:
        result = await session.execute(select(EventLog))
        logs = list(result.scalars().all())
        assert len(logs) == 1
        assert logs[0].routing_key == "staff.created"
        assert json.loads(logs[0].payload) == {"userId": "u-1", "role": "waiter"}
        assert logs[0].business_id is None


@pytest.mark.asyncio
async def test_handle_any_event_stores_payload_business_id(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)

    await _handle(session_factory, "payment.completed", {"orderId": "o-1", "businessId": "biz-a", "amount": 10.0})

    async with session_factory() as session:
        result = await session.execute(select(EventLog))
        log = result.scalar_one()
        assert log.business_id == "biz-a"


@pytest.mark.asyncio
async def test_order_created_upserts_order_mirror(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)

    await _handle(
        session_factory,
        "order.created",
        {
            "orderId": "order-1",
            "locationId": "loc-1",
            "channel": "dine_in",
            "status": "open",
            "total": 100.0,
            "createdAt": "2024-01-01T12:00:00+00:00",
            "version": 1,
            "occurredAt": "2024-01-01T12:00:00+00:00",
        },
    )

    async with session_factory() as session:
        result = await session.execute(select(ReportingOrder).where(ReportingOrder.id == "order-1"))
        order = result.scalar_one()
        assert order.location_id == "loc-1"
        assert order.status == "open"
        assert order.total == 100.0


@pytest.mark.asyncio
async def test_order_created_captures_created_by(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)

    await _handle(
        session_factory,
        "order.created",
        {
            "orderId": "order-2",
            "locationId": "loc-1",
            "channel": "dine_in",
            "status": "open",
            "total": 100.0,
            "createdBy": "user-1",
            "version": 1,
        },
    )

    async with session_factory() as session:
        result = await session.execute(select(ReportingOrder).where(ReportingOrder.id == "order-2"))
        assert result.scalar_one().created_by == "user-1"


@pytest.mark.asyncio
async def test_order_updated_and_payment_completed_transition_status(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)

    await _handle(
        session_factory,
        "order.created",
        {
            "orderId": "order-1",
            "locationId": "loc-1",
            "channel": "dine_in",
            "status": "open",
            "total": 50.0,
            "version": 1,
        },
    )
    await _handle(session_factory, "order.updated", {"orderId": "order-1", "status": "submitted", "version": 2})

    async with session_factory() as session:
        result = await session.execute(select(ReportingOrder).where(ReportingOrder.id == "order-1"))
        assert result.scalar_one().status == "submitted"

    await _handle(session_factory, "payment.completed", {"orderId": "order-1", "amount": 50.0})

    async with session_factory() as session:
        result = await session.execute(select(ReportingOrder).where(ReportingOrder.id == "order-1"))
        assert result.scalar_one().status == "paid"


@pytest.mark.asyncio
async def test_order_updated_for_unknown_order_upserts(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)

    await _handle(
        session_factory,
        "order.updated",
        {
            "orderId": "late-order",
            "locationId": "loc-1",
            "status": "submitted",
            "version": 2,
        },
    )

    async with session_factory() as session:
        result = await session.execute(select(ReportingOrder).where(ReportingOrder.id == "late-order"))
        assert result.scalar_one().status == "submitted"


@pytest.mark.asyncio
async def test_stale_order_event_does_not_overwrite_newer_projection(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)

    await _handle(
        session_factory,
        "order.created",
        {"orderId": "order-1", "locationId": "loc-1", "status": "open", "total": 10.0, "version": 1},
    )
    await _handle(
        session_factory,
        "order.updated",
        {"orderId": "order-1", "status": "ready", "total": 10.0, "version": 3},
    )
    await _handle(
        session_factory,
        "order.updated",
        {"orderId": "order-1", "status": "submitted", "total": 10.0, "version": 2},
    )

    async with session_factory() as session:
        result = await session.execute(select(ReportingOrder).where(ReportingOrder.id == "order-1"))
        row = result.scalar_one()
        assert row.status == "ready"
        assert row.version == 3


@pytest.mark.asyncio
async def test_projected_item_revenue_is_net_of_comp_discount_and_order_total(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)

    await _handle(
        session_factory,
        "order.created",
        {
            "orderId": "order-net",
            "locationId": "loc-1",
            "status": "paid",
            "total": 90.0,
            "version": 1,
            "items": [
                {
                    "id": "line-1",
                    "menuItemName": "Burger",
                    "qty": 1,
                    "unitPrice": 100.0,
                    "discountAmount": 10.0,
                    "isComped": False,
                    "status": "served",
                },
                {
                    "id": "line-2",
                    "menuItemName": "Fries",
                    "qty": 1,
                    "unitPrice": 20.0,
                    "isComped": True,
                    "status": "served",
                },
            ],
        },
    )

    async with session_factory() as session:
        result = await session.execute(select(ReportingOrderItem).where(ReportingOrderItem.order_id == "order-net"))
        rows = {row.menu_item_name: row for row in result.scalars()}
        assert rows["Burger"].revenue == 90.0
        assert rows["Fries"].revenue == 0.0
        assert rows["Fries"].is_comped is True
