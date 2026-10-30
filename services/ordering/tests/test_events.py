"""Tests for outbox enqueue call sites and the payment.completed consumer handler."""

import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Business, Location, MenuItem, Order, Outbox, User
from app.db.session import Base
from app.modules.ordering.events import (
    handle_payment_completed,
    handle_payment_refunded,
    handle_realtime,
    slim_ws_payload,
)


@pytest.mark.asyncio
async def test_create_order_enqueues_order_created(
    client: AsyncClient,
    business: Business,
    location: Location,
    manager_user: tuple[User, str],
    db: AsyncSession,
):
    user, token = manager_user
    business_id = user.business_id
    location_id = location.id
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location_id, "channel": "dine_in", "guestCount": 2},
        headers=headers,
    )
    assert resp.status_code == 201
    order_id = resp.json()["id"]

    db.expire_all()
    row = (await db.execute(select(Outbox))).scalar_one()
    payload = json.loads(row.payload)
    assert row.routing_key == "order.created"
    assert payload["orderId"] == order_id
    assert payload["version"] == 1
    assert "occurredAt" in payload
    assert payload["locationId"] == location_id
    assert payload["businessId"] == business_id
    assert payload["createdBy"] == resp.json()["createdBy"]
    assert payload["eventId"]


@pytest.mark.asyncio
async def test_submit_order_enqueues_order_updated(
    client: AsyncClient,
    location: Location,
    manager_user: tuple[User, str],
    db: AsyncSession,
):
    user, token = manager_user
    business_id = user.business_id
    location_id = location.id
    headers = {"Authorization": f"Bearer {token}"}

    order_id = (
        await client.post(
            "/api/v1/orders",
            json={"locationId": location_id, "channel": "dine_in", "guestCount": 2},
            headers=headers,
        )
    ).json()["id"]

    resp = await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)
    assert resp.status_code == 200

    db.expire_all()
    row = (
        await db.execute(select(Outbox).where(Outbox.routing_key == "order.updated").order_by(Outbox.occurred_at.desc()))
    ).scalars().first()
    assert row is not None
    payload = json.loads(row.payload)
    assert payload["orderId"] == order_id
    assert payload["status"] == "submitted"
    assert payload["version"] == 2
    assert "occurredAt" in payload
    assert payload["businessId"] == business_id


@pytest.mark.asyncio
async def test_fire_course_publishes_order_item_fired(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
):
    user, token = manager_user
    business_id = user.business_id
    location_id = location.id
    headers = {"Authorization": f"Bearer {token}"}

    item = MenuItem(category_id="cat-1", name="Steak", price=80.0, tax_rate=0.17, default_fire_course=2)
    db.add(item)
    await db.flush()
    menu_item_id = item.id

    order_id = (
        await client.post(
            "/api/v1/orders",
            json={"locationId": location_id, "channel": "dine_in", "guestCount": 2},
            headers=headers,
        )
    ).json()["id"]
    item_resp = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": menu_item_id, "qty": 1},
            headers=headers,
        )
    ).json()
    await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)

    resp = await client.post(f"/api/v1/orders/{order_id}/fire-course", json={"course": 2}, headers=headers)
    assert resp.status_code == 200

    db.expire_all()
    rows = (await db.execute(select(Outbox))).scalars().all()
    keys = [row.routing_key for row in rows]
    assert "order.item_fired" in keys
    assert "order.updated" in keys
    payload = json.loads(next(row.payload for row in rows if row.routing_key == "order.item_fired"))
    assert payload["orderId"] == order_id
    assert payload["itemId"] == item_resp["id"]
    assert payload["menuItemId"] == menu_item_id
    assert payload["businessId"] == business_id


def _fired_payloads(rows: list[Outbox]) -> list[dict]:
    return [json.loads(row.payload) for row in rows if row.routing_key == "order.item_fired"]


@pytest.mark.asyncio
async def test_submit_and_add_enqueue_item_fired_once(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
):
    user, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    burger = MenuItem(category_id="cat-1", name="Burger", price=45.0, tax_rate=0.17, default_fire_course=1)
    steak = MenuItem(category_id="cat-1", name="Steak", price=80.0, tax_rate=0.17, default_fire_course=2)
    db.add_all([burger, steak])
    await db.flush()
    burger_id = burger.id
    steak_id = steak.id

    order_id = (
        await client.post(
            "/api/v1/orders",
            json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
            headers=headers,
        )
    ).json()["id"]
    first = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": burger_id, "qty": 1},
            headers=headers,
        )
    ).json()
    course_two = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": steak_id, "qty": 1},
            headers=headers,
        )
    ).json()

    assert (await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)).status_code == 200
    db.expire_all()
    rows = (await db.execute(select(Outbox))).scalars().all()
    fired = _fired_payloads(rows)
    assert [row["itemId"] for row in fired] == [first["id"]]

    assert (await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)).status_code == 400
    db.expire_all()
    assert len(_fired_payloads((await db.execute(select(Outbox))).scalars().all())) == 1

    second = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": burger_id, "qty": 1},
            headers=headers,
        )
    ).json()
    db.expire_all()
    fired_ids = [row["itemId"] for row in _fired_payloads((await db.execute(select(Outbox))).scalars().all())]
    assert fired_ids == [first["id"], second["id"]]

    assert (await client.post(f"/api/v1/orders/{order_id}/fire-course", json={"course": 2}, headers=headers)).status_code == 200
    db.expire_all()
    fired_ids = [row["itemId"] for row in _fired_payloads((await db.execute(select(Outbox))).scalars().all())]
    assert fired_ids == [first["id"], second["id"], course_two["id"]]

    assert (await client.post(f"/api/v1/orders/{order_id}/fire-course", json={"course": 2}, headers=headers)).status_code == 400
    db.expire_all()
    assert len(_fired_payloads((await db.execute(select(Outbox))).scalars().all())) == 3


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

    async with session_factory() as session:
        await handle_payment_completed("payment.completed", {"orderId": order_id, "amount": 42.0}, session)
        await session.commit()

    async with session_factory() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        paid = result.scalar_one()
        assert paid.status == "paid"
        assert paid.version == 1


@pytest.mark.asyncio
async def test_handle_payment_completed_ignores_unknown_order(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await handle_payment_completed("payment.completed", {"orderId": "does-not-exist"}, session)
        await session.commit()


@pytest.mark.asyncio
async def test_handle_payment_refunded_marks_paid_order_served(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        order = Order(location_id="loc-1", channel="dine_in", status="paid", total=42.0)
        session.add(order)
        await session.commit()
        order_id = order.id

    async with session_factory() as session:
        await handle_payment_refunded("payment.refunded", {"orderId": order_id}, session)
        await session.commit()

    async with session_factory() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        reopened = result.scalar_one()
        assert reopened.status == "served"


async def test_handle_payment_completed_missing_order_id_is_noop(events_engine):
    session_factory = async_sessionmaker(events_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await handle_payment_completed("payment.completed", {}, session)
        await session.commit()


@pytest.mark.asyncio
async def test_handle_realtime_publishes_slim_catalog_event():
    with patch("app.modules.ordering.events.publish_ws", new_callable=AsyncMock) as mock_publish:
        await handle_realtime(
            "catalog.item_updated",
            {"locationId": "loc-1", "itemId": "item-1", "price": 45.0, "createdBy": "staff-1"},
            None,  # type: ignore[arg-type]
        )

    mock_publish.assert_awaited_once()
    location_id, event = mock_publish.await_args.args
    assert location_id == "loc-1"
    assert event["type"] == "menu.item_updated"
    assert event["payload"] == {"itemId": "item-1", "locationId": "loc-1"}
    assert "price" not in event["payload"]
    assert "createdBy" not in event["payload"]


@pytest.mark.asyncio
async def test_handle_realtime_missing_location_id_is_noop():
    with patch("app.modules.ordering.events.publish_ws", new_callable=AsyncMock) as mock_publish:
        await handle_realtime("catalog.item_updated", {"itemId": "item-1"}, None)  # type: ignore[arg-type]

    mock_publish.assert_not_awaited()


def test_slim_ws_payload_drops_totals_notes_and_staff():
    payload = slim_ws_payload(
        "order.updated",
        {
            "orderId": "o-1",
            "locationId": "loc-1",
            "status": "submitted",
            "total": 99.0,
            "notes": "secret",
            "createdBy": "user-1",
            "tableName": "T1",
            "orderNumber": 12,
        },
    )
    assert payload == {
        "orderId": "o-1",
        "id": "o-1",
        "locationId": "loc-1",
        "status": "submitted",
        "tableName": "T1",
        "orderNumber": 12,
    }


@pytest.mark.asyncio
async def test_item_status_change_enqueues_order_updated(
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

    resp = await client.patch(
        f"/api/v1/orders/{order_id}/items/{item_id}/status",
        json={"status": "preparing"},
        headers=headers,
    )
    assert resp.status_code == 200
    db.expire_all()
    rows = list((await db.execute(select(Outbox).where(Outbox.routing_key == "order.updated"))).scalars().all())
    assert any(json.loads(row.payload)["orderId"] == order_id for row in rows)


@pytest.mark.asyncio
async def test_cancel_item_enqueues_order_updated_with_new_total(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    cola = MenuItem(category_id="cat-1", name="Cola", price=12.0)
    burger = MenuItem(category_id="cat-1", name="Burger", price=68.0)
    db.add_all([cola, burger])
    await db.flush()

    order_id = (
        await client.post(
            "/api/v1/orders",
            json={"locationId": location.id, "channel": "takeaway"},
            headers=headers,
        )
    ).json()["id"]
    cola_line = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": cola.id, "qty": 1},
            headers=headers,
        )
    ).json()
    await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": burger.id, "qty": 1},
        headers=headers,
    )
    submitted = (await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)).json()
    before = submitted["total"]

    resp = await client.patch(
        f"/api/v1/orders/{order_id}/items/{cola_line['id']}/status",
        json={"status": "cancelled"},
        headers=headers,
    )
    assert resp.status_code == 200
    after = (await client.get(f"/api/v1/orders/{order_id}", headers=headers)).json()
    assert after["total"] < before

    db.expire_all()
    row = (
        await db.execute(
            select(Outbox).where(Outbox.routing_key == "order.updated").order_by(Outbox.occurred_at.desc())
        )
    ).scalars().first()
    assert row is not None
    payload = json.loads(row.payload)
    assert payload["orderId"] == order_id
    assert payload["total"] == after["total"]
    assert "total" in payload
