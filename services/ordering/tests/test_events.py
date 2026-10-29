"""Tests for the RabbitMQ event-bus integration: publish call sites (mocked) and the
`payment.completed` consumer handler (against a real in-memory DB)."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Business, Location, MenuItem, Order, User
from app.db.session import Base
from app.modules.ordering.events import handle_catalog_item_updated, handle_payment_completed


@pytest.mark.asyncio
async def test_create_order_publishes_order_created(
    client: AsyncClient,
    business: Business,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    with patch("smartserve_shared.mq.publish", new_callable=AsyncMock) as mock_publish:
        resp = await client.post(
            "/api/v1/orders",
            json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
            headers=headers,
        )
    assert resp.status_code == 201
    order_id = resp.json()["id"]

    mock_publish.assert_awaited_once()
    _, routing_key, payload = mock_publish.await_args.args
    assert routing_key == "order.created"
    assert payload["orderId"] == order_id
    assert payload["locationId"] == location.id
    assert payload["createdBy"] == resp.json()["createdBy"]


@pytest.mark.asyncio
async def test_submit_order_publishes_order_updated(
    client: AsyncClient,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    order_id = (
        await client.post(
            "/api/v1/orders",
            json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
            headers=headers,
        )
    ).json()["id"]

    with patch("smartserve_shared.mq.publish", new_callable=AsyncMock) as mock_publish:
        resp = await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)
    assert resp.status_code == 200

    mock_publish.assert_awaited_once()
    _, routing_key, payload = mock_publish.await_args.args
    assert routing_key == "order.updated"
    assert payload["orderId"] == order_id
    assert payload["status"] == "submitted"


@pytest.mark.asyncio
async def test_fire_course_publishes_order_item_fired(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    item = MenuItem(category_id="cat-1", name="Steak", price=80.0, tax_rate=0.17, default_fire_course=2)
    db.add(item)
    await db.flush()

    order_id = (
        await client.post(
            "/api/v1/orders",
            json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
            headers=headers,
        )
    ).json()["id"]
    item_resp = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": item.id, "qty": 1},
            headers=headers,
        )
    ).json()
    await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)

    with patch("smartserve_shared.mq.publish", new_callable=AsyncMock) as mock_publish:
        resp = await client.post(f"/api/v1/orders/{order_id}/fire-course", json={"course": 2}, headers=headers)
    assert resp.status_code == 200

    mock_publish.assert_awaited_once()
    _, routing_key, payload = mock_publish.await_args.args
    assert routing_key == "order.item_fired"
    assert payload["orderId"] == order_id
    assert payload["itemId"] == item_resp["id"]
    assert payload["menuItemId"] == item.id


@pytest_asyncio.fixture
async def events_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_handle_payment_completed_marks_order_paid(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        order = Order(location_id="loc-1", channel="dine_in", status="served", total=42.0)
        session.add(order)
        await session.commit()
        order_id = order.id

    with patch("app.modules.ordering.events.AsyncSessionLocal", session_factory):
        await handle_payment_completed("payment.completed", {"orderId": order_id, "amount": 42.0})

    async with session_factory() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        assert result.scalar_one().status == "paid"


@pytest.mark.asyncio
async def test_handle_payment_completed_ignores_unknown_order(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)
    with patch("app.modules.ordering.events.AsyncSessionLocal", session_factory):
        # Should not raise even though the order doesn't exist
        await handle_payment_completed("payment.completed", {"orderId": "does-not-exist"})


@pytest.mark.asyncio
async def test_handle_payment_completed_missing_order_id_is_noop(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)
    with patch("app.modules.ordering.events.AsyncSessionLocal", session_factory):
        await handle_payment_completed("payment.completed", {})


@pytest.mark.asyncio
async def test_handle_catalog_item_updated_broadcasts_to_location():
    with patch("app.modules.ordering.events.broadcast", new_callable=AsyncMock) as mock_broadcast:
        await handle_catalog_item_updated(
            "catalog.item_updated",
            {"locationId": "loc-1", "itemId": "item-1", "price": 45.0},
        )

    mock_broadcast.assert_awaited_once()
    location_id, event = mock_broadcast.await_args.args
    assert location_id == "loc-1"
    assert event["type"] == "menu.item_updated"
    assert event["locationId"] == "loc-1"
    assert event["payload"]["itemId"] == "item-1"
    assert "timestamp" in event


@pytest.mark.asyncio
async def test_handle_catalog_item_updated_missing_location_id_is_noop():
    with patch("app.modules.ordering.events.broadcast", new_callable=AsyncMock) as mock_broadcast:
        await handle_catalog_item_updated("catalog.item_updated", {"itemId": "item-1"})

    mock_broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_submit_order_broadcasts_websocket_event(
    client: AsyncClient,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    order_id = (
        await client.post(
            "/api/v1/orders",
            json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
            headers=headers,
        )
    ).json()["id"]

    with patch("app.modules.ordering.router.broadcast_event", new_callable=AsyncMock) as mock_broadcast:
        resp = await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)

    assert resp.status_code == 200
    mock_broadcast.assert_awaited_once()
    location_id, event_type, payload = mock_broadcast.await_args.args
    assert location_id == location.id
    assert event_type == "order.updated"
    assert payload["orderId"] == order_id
    assert payload["status"] == "submitted"


@pytest.mark.asyncio
async def test_item_status_change_broadcasts_websocket_event(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    item = MenuItem(category_id="cat-1", name="Cola", price=10.0, tax_rate=0.17)
    db.add(item)
    await db.flush()

    order_id = (
        await client.post(
            "/api/v1/orders",
            json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
            headers=headers,
        )
    ).json()["id"]
    item_id = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": item.id, "qty": 1},
            headers=headers,
        )
    ).json()["id"]
    await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)

    with patch("app.modules.ordering.router.broadcast_event", new_callable=AsyncMock) as mock_broadcast:
        resp = await client.patch(
            f"/api/v1/orders/{order_id}/items/{item_id}/status",
            json={"status": "preparing"},
            headers=headers,
        )

    assert resp.status_code == 200
    mock_broadcast.assert_awaited_once()
    location_id, event_type, payload = mock_broadcast.await_args.args
    assert location_id == location.id
    assert event_type == "order.item_status_changed"
    assert payload["orderId"] == order_id
    assert payload["itemId"] == item_id
    assert payload["status"] == "preparing"
    assert payload["orderStatus"] == "preparing"
