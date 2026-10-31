"""Integration tests for order lifecycle."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from smartserve_shared.security import hash_password
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, Location, MenuCategory, MenuItem, Table, User
from app.modules.ordering.schemas import OrderCreate
from app.modules.ordering.service import OrderService


def _patch_display_device(monkeypatch: pytest.MonkeyPatch, location_id: str) -> None:
    async def _device(_raw: str | None) -> dict:
        return {"locationId": location_id, "type": "display"}

    monkeypatch.setattr("app.modules.ordering.router.device_for_token", _device)


@pytest.mark.asyncio
async def test_order_lifecycle(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()

    item = MenuItem(
        category_id="cat-1",
        name="Burger",
        price=45.0,
        tax_rate=0.17,
    )
    db.add(item)
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}

    # Create order
    resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
        headers=headers,
    )
    assert resp.status_code == 201
    order_id = resp.json()["id"]
    assert resp.json()["status"] == "open"
    assert resp.json()["guestCount"] == 2

    # Add item to order
    resp = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": item.id, "qty": 2},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["menuItemName"] == "Burger"

    # Submit order
    resp = await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"

    # Cannot submit again
    resp = await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)
    assert resp.status_code == 400

    # Cancel from submitted
    resp = await client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_dine_in_order_requires_guest_count(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "dine_in"},
        headers=headers,
    )
    assert resp.status_code == 400

    resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "takeaway"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["tableName"] is None


@pytest.mark.asyncio
async def test_daily_order_numbers_per_location_and_business_day(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    loc_a = Location(business_id=business.id, name="A", timezone="Asia/Jerusalem")
    loc_b = Location(business_id=business.id, name="B", timezone="Asia/Jerusalem")
    db.add_all([loc_a, loc_b])
    await db.flush()

    numbers_a = []
    first_a: dict | None = None
    for _ in range(3):
        resp = await client.post(
            "/api/v1/orders",
            json={"locationId": loc_a.id, "channel": "takeaway"},
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        first_a = first_a or body
        numbers_a.append(body["orderNumber"])
    assert numbers_a == [1, 2, 3]
    assert first_a is not None

    other = await client.post(
        "/api/v1/orders",
        json={"locationId": loc_b.id, "channel": "takeaway"},
        headers=headers,
    )
    assert other.status_code == 201
    assert other.json()["orderNumber"] == 1

    early = datetime(2026, 10, 31, 2, 0, tzinfo=ZoneInfo("Asia/Jerusalem"))
    overnight = await OrderService(db).create_order(
        OrderCreate(location_id=loc_a.id, channel="takeaway"),
        created_by="test",
        business_id=business.id,
        now=early,
    )
    assert overnight.business_date == date(2026, 10, 30)
    same_day = date.fromisoformat(str(first_a["businessDate"])) == date(2026, 10, 30)
    assert overnight.order_number == (4 if same_day else 1)


@pytest.mark.asyncio
async def test_order_responses_include_table_name(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
    monkeypatch: pytest.MonkeyPatch,
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    table = Table(location_id=location.id, name="T3", capacity=4)
    db.add(table)
    await db.flush()

    created = await client.post(
        "/api/v1/orders",
        json={
            "locationId": location.id,
            "channel": "dine_in",
            "guestCount": 2,
            "tableId": table.id,
        },
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["tableName"] == "T3"
    order_id = created.json()["id"]

    detail = await client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert detail.json()["tableName"] == "T3"

    listed = await client.get(f"/api/v1/locations/{location.id}/orders", headers=headers)
    match = next(row for row in listed.json() if row["id"] == order_id)
    assert match["tableName"] == "T3"

    _patch_display_device(monkeypatch, location.id)
    display = await client.get("/api/v1/public/display/orders", headers={"X-Device-Token": "display-token"})
    assert display.status_code == 200


async def _make_order_with_two_items(client: AsyncClient, db: AsyncSession, business: Business, headers: dict):
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    burger = MenuItem(category_id="cat-1", name="Burger", price=45.0, tax_rate=0.17)
    fries = MenuItem(category_id="cat-1", name="Fries", price=15.0, tax_rate=0.17)
    db.add_all([burger, fries])
    await db.flush()

    order_resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
        headers=headers,
    )
    order_id = order_resp.json()["id"]

    burger_item = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": burger.id, "qty": 1},
            headers=headers,
        )
    ).json()
    fries_item = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": fries.id, "qty": 1},
            headers=headers,
        )
    ).json()
    return location, order_id, burger_item, fries_item


@pytest.mark.asyncio
async def test_assign_guests_within_same_order(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    _, order_id, burger_item, fries_item = await _make_order_with_two_items(client, db, business, headers)

    # Tagging guests never creates a new order — it's an in-place update on the same order.
    resp = await client.post(
        f"/api/v1/orders/{order_id}/items/assign-guests",
        json={
            "assignments": [
                {"itemId": burger_item["id"], "guestNumber": 1},
                {"itemId": fries_item["id"], "guestNumber": 2},
            ]
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == order_id
    assert body["status"] == "open"
    guest_by_item = {i["id"]: i["guestNumber"] for i in body["items"]}
    assert guest_by_item[burger_item["id"]] == 1
    assert guest_by_item[fries_item["id"]] == 2

    # Assignment is optional and can be cleared back to shared (None)
    resp = await client.post(
        f"/api/v1/orders/{order_id}/items/assign-guests",
        json={"assignments": [{"itemId": burger_item["id"], "guestNumber": None}]},
        headers=headers,
    )
    assert resp.status_code == 200
    guest_by_item = {i["id"]: i["guestNumber"] for i in resp.json()["items"]}
    assert guest_by_item[burger_item["id"]] is None


@pytest.mark.asyncio
async def test_order_records_created_by_from_authenticated_user(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    manager, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["createdBy"] == manager.id

    # A client-supplied createdBy in the request body must be ignored — it's always
    # server-derived from the authenticated JWT, never trusted from the client.
    resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "dine_in", "guestCount": 1, "createdBy": "someone-else"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["createdBy"] == manager.id


@pytest.mark.asyncio
async def test_order_item_captures_category_snapshot(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()

    category = MenuCategory(name="Burgers")
    db.add(category)
    await db.flush()

    item = MenuItem(category_id=category.id, name="Cheeseburger", price=52.0, tax_rate=0.17)
    db.add(item)
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}
    order_resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "dine_in", "guestCount": 1},
        headers=headers,
    )
    order_id = order_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": item.id, "qty": 1},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["categoryId"] == category.id
    assert body["categoryName"] == "Burgers"


@pytest.mark.asyncio
async def test_order_item_category_snapshot_is_none_when_category_missing(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    """A menu item whose category_id doesn't resolve to a real MenuCategory row (e.g. the
    catalog category was deleted, or test data left dangling) shouldn't error — the snapshot
    just stays unset."""
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()

    item = MenuItem(category_id="cat-does-not-exist", name="Fries", price=15.0, tax_rate=0.17)
    db.add(item)
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}
    order_resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "dine_in", "guestCount": 1},
        headers=headers,
    )
    order_id = order_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": item.id, "qty": 1},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["categoryId"] == "cat-does-not-exist"
    assert body["categoryName"] is None


@pytest.mark.asyncio
async def test_item_discount_and_comp(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    _, order_id, burger_item, fries_item = await _make_order_with_two_items(client, db, business, headers)

    # 10% discount on the burger (45.0 * 0.10 = 4.5)
    resp = await client.post(
        f"/api/v1/orders/{order_id}/items/discount",
        json={"items": [{"itemId": burger_item["id"]}], "discountType": "percent", "discountValue": 10},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    burger = next(i for i in body["items"] if i["id"] == burger_item["id"])
    assert burger["discountAmount"] == pytest.approx(4.5)
    # subtotal = (45 - 4.5) + 15 = 55.5
    assert body["subtotal"] == pytest.approx(55.5)

    # Mark the fries on the house — it should drop out of the subtotal entirely
    resp = await client.post(
        f"/api/v1/orders/{order_id}/items/comp",
        json={"items": [{"itemId": fries_item["id"]}], "comped": True},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    fries = next(i for i in body["items"] if i["id"] == fries_item["id"])
    assert fries["isComped"] is True
    assert fries["compedBy"] is not None
    assert body["subtotal"] == pytest.approx(40.5)


@pytest.mark.asyncio
async def test_delete_submitted_item_requires_manager_override(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    manager, token = manager_user
    manager.pin_hash = hash_password("1234")
    await db.flush()
    headers = {"Authorization": f"Bearer {token}"}
    location, order_id, burger_item, fries_item = await _make_order_with_two_items(client, db, business, headers)

    # Deleting while still open needs no override
    resp = await client.post(
        f"/api/v1/orders/{order_id}/items/delete",
        json={"items": [{"itemId": fries_item["id"]}]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1

    await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)

    # Once submitted, deleting without an override is rejected
    resp = await client.post(
        f"/api/v1/orders/{order_id}/items/delete",
        json={"items": [{"itemId": burger_item["id"]}]},
        headers=headers,
    )
    assert resp.status_code == 400

    # An invalid PIN is rejected too
    resp = await client.post(
        f"/api/v1/orders/{order_id}/items/delete",
        json={
            "items": [{"itemId": burger_item["id"]}],
            "override": {"managerUserId": manager.id, "pin": "0000", "reason": "wrong item"},
        },
        headers=headers,
    )
    assert resp.status_code == 401

    # Correct manager PIN + reason succeeds
    resp = await client.post(
        f"/api/v1/orders/{order_id}/items/delete",
        json={
            "items": [{"itemId": burger_item["id"]}],
            "override": {"managerUserId": manager.id, "pin": "1234", "reason": "wrong item"},
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_manager_override_pin_lockout(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    manager, token = manager_user
    manager.pin_hash = hash_password("1234")
    await db.flush()
    headers = {"Authorization": f"Bearer {token}"}
    _location, order_id, burger_item, _fries_item = await _make_order_with_two_items(client, db, business, headers)
    await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)

    wrong = {
        "items": [{"itemId": burger_item["id"]}],
        "override": {"managerUserId": manager.id, "pin": "0000", "reason": "wrong item"},
    }
    for i in range(4):
        resp = await client.post(f"/api/v1/orders/{order_id}/items/delete", json=wrong, headers=headers)
        assert resp.status_code == 401, i

    fifth = await client.post(f"/api/v1/orders/{order_id}/items/delete", json=wrong, headers=headers)
    assert fifth.status_code == 423
    assert int(fifth.headers["Retry-After"]) > 0

    correct = await client.post(
        f"/api/v1/orders/{order_id}/items/delete",
        json={
            "items": [{"itemId": burger_item["id"]}],
            "override": {"managerUserId": manager.id, "pin": "1234", "reason": "wrong item"},
        },
        headers=headers,
    )
    assert correct.status_code == 423


@pytest.mark.asyncio
async def test_partial_quantity_split_on_item_action(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    location, order_id, burger_item, _fries_item = await _make_order_with_two_items(client, db, business, headers)

    # Bump the burger to qty 3 so we can split off a partial quantity for a bulk action
    resp = await client.patch(
        f"/api/v1/orders/{order_id}/items/{burger_item['id']}",
        json={"qty": 3},
        headers=headers,
    )
    assert resp.status_code == 200

    # Comp only 1 of the 3 burgers — should split into a qty=1 comped row + qty=2 untouched row
    resp = await client.post(
        f"/api/v1/orders/{order_id}/items/comp",
        json={"items": [{"itemId": burger_item["id"], "quantity": 1}], "comped": True},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    burgers = [i for i in body["items"] if i["menuItemName"] == "Burger"]
    assert len(burgers) == 2
    comped = next(i for i in burgers if i["isComped"])
    remaining = next(i for i in burgers if not i["isComped"])
    assert comped["qty"] == 1
    assert remaining["qty"] == 2
    # subtotal = (2 * 45, uncomped burger) + 15 fries = 105
    assert body["subtotal"] == pytest.approx(105.0)


@pytest.mark.asyncio
async def test_fire_course(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    starter = MenuItem(category_id="cat-1", name="Soup", price=20.0, tax_rate=0.17)
    main_course = MenuItem(
        category_id="cat-1",
        name="Steak",
        price=80.0,
        tax_rate=0.17,
        default_fire_course=2,
    )
    db.add_all([starter, main_course])
    await db.flush()

    order_resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
        headers=headers,
    )
    order_id = order_resp.json()["id"]

    starter_item = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": starter.id, "qty": 1},
            headers=headers,
        )
    ).json()
    assert starter_item["fireCourse"] == 1
    assert starter_item["status"] == "pending"

    main_item = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": main_course.id, "qty": 1},
            headers=headers,
        )
    ).json()
    assert main_item["fireCourse"] == 2
    assert main_item["status"] == "held"

    # Cannot fire a course before the order has been submitted to the kitchen
    resp = await client.post(f"/api/v1/orders/{order_id}/fire-course", json={"course": 2}, headers=headers)
    assert resp.status_code == 400

    resp = await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)
    assert resp.status_code == 200

    # No held items for course 3
    resp = await client.post(f"/api/v1/orders/{order_id}/fire-course", json={"course": 3}, headers=headers)
    assert resp.status_code == 400

    resp = await client.post(f"/api/v1/orders/{order_id}/fire-course", json={"course": 2}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["firedCourses"] == [2]
    fired_item = next(i for i in body["items"] if i["id"] == main_item["id"])
    assert fired_item["status"] == "pending"


@pytest.mark.asyncio
async def test_reorder_order_items(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    burger = MenuItem(category_id="cat-1", name="Burger", price=45.0, tax_rate=0.17)
    fries = MenuItem(category_id="cat-1", name="Fries", price=15.0, tax_rate=0.17)
    db.add_all([burger, fries])
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}

    order_resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
        headers=headers,
    )
    order_id = order_resp.json()["id"]

    first = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": burger.id, "qty": 1},
        headers=headers,
    )
    second = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": fries.id, "qty": 1},
        headers=headers,
    )
    first_id, second_id = first.json()["id"], second.json()["id"]

    # Items come back in insertion order by default
    order = (await client.get(f"/api/v1/orders/{order_id}", headers=headers)).json()
    assert [i["id"] for i in order["items"]] == [first_id, second_id]

    # Reorder: move fries to the front
    resp = await client.post(
        f"/api/v1/orders/{order_id}/items/reorder",
        json={"ids": [second_id, first_id]},
        headers=headers,
    )
    assert resp.status_code == 204

    order = (await client.get(f"/api/v1/orders/{order_id}", headers=headers)).json()
    assert [i["id"] for i in order["items"]] == [second_id, first_id]

    empty = await client.post(
        f"/api/v1/orders/{order_id}/items/reorder",
        json={},
        headers=headers,
    )
    assert empty.status_code == 422


@pytest.mark.asyncio
async def test_remove_order_item(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    burger = MenuItem(category_id="cat-1", name="Burger", price=45.0, tax_rate=0.17)
    fries = MenuItem(category_id="cat-1", name="Fries", price=15.0, tax_rate=0.17)
    db.add_all([burger, fries])
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}

    order_resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
        headers=headers,
    )
    order_id = order_resp.json()["id"]

    burger_item = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": burger.id, "qty": 1},
            headers=headers,
        )
    ).json()
    fries_item = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": fries.id, "qty": 1},
            headers=headers,
        )
    ).json()

    # Removing an item on an open order deletes it outright and recalculates totals
    resp = await client.delete(f"/api/v1/orders/{order_id}/items/{fries_item['id']}", headers=headers)
    assert resp.status_code == 204

    order = (await client.get(f"/api/v1/orders/{order_id}", headers=headers)).json()
    assert [i["id"] for i in order["items"]] == [burger_item["id"]]
    assert order["subtotal"] == 45.0

    # Once submitted, items can no longer be removed outright (only cancelled)
    await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)
    resp = await client.delete(f"/api/v1/orders/{order_id}/items/{burger_item['id']}", headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_order_item(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    burger = MenuItem(category_id="cat-1", name="Burger", price=45.0, tax_rate=0.17)
    db.add(burger)
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}

    order_id = (
        await client.post(
            "/api/v1/orders",
            json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
            headers=headers,
        )
    ).json()["id"]

    item = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": burger.id, "qty": 1},
            headers=headers,
        )
    ).json()

    # Bump quantity and add a note
    resp = await client.patch(
        f"/api/v1/orders/{order_id}/items/{item['id']}",
        json={"qty": 3, "notes": "well done"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["qty"] == 3
    assert resp.json()["notes"] == "well done"

    order = (await client.get(f"/api/v1/orders/{order_id}", headers=headers)).json()
    assert order["subtotal"] == 135.0

    # Cannot edit a served item
    await client.patch(
        f"/api/v1/orders/{order_id}/items/{item['id']}/status",
        json={"status": "preparing"},
        headers=headers,
    )
    await client.patch(
        f"/api/v1/orders/{order_id}/items/{item['id']}/status",
        json={"status": "ready"},
        headers=headers,
    )
    await client.patch(
        f"/api/v1/orders/{order_id}/items/{item['id']}/status",
        json={"status": "served"},
        headers=headers,
    )
    resp = await client.patch(
        f"/api/v1/orders/{order_id}/items/{item['id']}",
        json={"qty": 5},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_add_item_rejects_trashed_menu_item(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    """A menu item that catalog has moved to trash (`deleted_at` set) must not be addable
    to a brand-new order — mirrors the existing `active` check, so a trashed item can't
    quietly leak back onto the order-taking grid via a stale client-side item id."""
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()

    item = MenuItem(category_id="cat-1", name="Discontinued Soup", price=20.0, tax_rate=0.17)
    item.deleted_at = datetime.now(UTC)
    db.add(item)
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}
    order_id = (
        await client.post(
            "/api/v1/orders",
            json={"locationId": location.id, "channel": "dine_in", "guestCount": 1},
            headers=headers,
        )
    ).json()["id"]

    resp = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": item.id, "qty": 1},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_trashing_menu_item_does_not_affect_existing_order_item(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    """Trashing (or even permanently deleting) a MenuItem after it's already been added to
    an order must never retroactively change that order — the order_item's own
    menu_item_name/unit_price snapshot is what's authoritative, not a live join."""
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()

    item = MenuItem(category_id="cat-1", name="Soon To Be Trashed", price=33.0, tax_rate=0.17)
    db.add(item)
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}
    order_id = (
        await client.post(
            "/api/v1/orders",
            json={"locationId": location.id, "channel": "dine_in", "guestCount": 1},
            headers=headers,
        )
    ).json()["id"]

    order_item = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": item.id, "qty": 2},
            headers=headers,
        )
    ).json()
    assert order_item["menuItemName"] == "Soon To Be Trashed"

    # Simulate catalog trashing the underlying item. Hard-delete is blocked by the
    # order_items.menu_item_id foreign key once SQLite enforces it (same as Postgres).
    item.deleted_at = datetime.now(UTC)
    await db.flush()

    order = (await client.get(f"/api/v1/orders/{order_id}", headers=headers)).json()
    assert order["items"][0]["menuItemName"] == "Soon To Be Trashed"
    assert order["items"][0]["unitPrice"] == 33.0
    assert order["subtotal"] == 66.0


# Note: payment-completes-order coverage lives in services/payments/tests, which builds
# the order fixture directly against its own DB mirror rather than via this service's HTTP API.


@pytest.mark.asyncio
async def test_kitchen_item_status_rolls_up_order_status_for_customer_display(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
    menu_item: MenuItem,
    monkeypatch: pytest.MonkeyPatch,
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
    item_id = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": menu_item.id, "qty": 1},
            headers=headers,
        )
    ).json()["id"]
    await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)

    _patch_display_device(monkeypatch, location.id)
    headers_display = {"X-Device-Token": "display-token"}
    display = (await client.get("/api/v1/public/display/orders", headers=headers_display)).json()
    assert set(display[0].keys()) == {"orderNumber", "status", "updatedAt"}
    assert display[0]["status"] == "submitted"

    await client.patch(
        f"/api/v1/orders/{order_id}/items/{item_id}/status",
        json={"status": "preparing"},
        headers=headers,
    )
    display = (await client.get("/api/v1/public/display/orders", headers=headers_display)).json()
    assert display[0]["status"] == "preparing"

    await client.patch(
        f"/api/v1/orders/{order_id}/items/{item_id}/status",
        json={"status": "ready"},
        headers=headers,
    )
    display = (await client.get("/api/v1/public/display/orders", headers=headers_display)).json()
    assert display[0]["status"] == "ready"
