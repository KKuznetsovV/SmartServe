"""Integration tests for order lifecycle."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models import Business, Location, MenuCategory, MenuItem, User


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
    category = MenuCategory(location_id=location.id, name="Food", sort_order=0)
    db.add(category)
    await db.flush()

    item = MenuItem(
        category_id=category.id,
        name="Burger",
        price=45.0,
        tax_rate=0.17,
        preparation_time_min=15,
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


async def _make_order_with_two_items(client: AsyncClient, db: AsyncSession, business: Business, headers: dict):
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    category = MenuCategory(location_id=location.id, name="Food", sort_order=0)
    db.add(category)
    await db.flush()
    burger = MenuItem(category_id=category.id, name="Burger", price=45.0, tax_rate=0.17, preparation_time_min=15)
    fries = MenuItem(category_id=category.id, name="Fries", price=15.0, tax_rate=0.17, preparation_time_min=10)
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
    category = MenuCategory(location_id=location.id, name="Food", sort_order=0)
    db.add(category)
    await db.flush()
    starter = MenuItem(category_id=category.id, name="Soup", price=20.0, tax_rate=0.17, preparation_time_min=5)
    main_course = MenuItem(
        category_id=category.id,
        name="Steak",
        price=80.0,
        tax_rate=0.17,
        preparation_time_min=20,
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
    category = MenuCategory(location_id=location.id, name="Food", sort_order=0)
    db.add(category)
    await db.flush()
    burger = MenuItem(category_id=category.id, name="Burger", price=45.0, tax_rate=0.17, preparation_time_min=15)
    fries = MenuItem(category_id=category.id, name="Fries", price=15.0, tax_rate=0.17, preparation_time_min=10)
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
    category = MenuCategory(location_id=location.id, name="Food", sort_order=0)
    db.add(category)
    await db.flush()
    burger = MenuItem(category_id=category.id, name="Burger", price=45.0, tax_rate=0.17, preparation_time_min=15)
    fries = MenuItem(category_id=category.id, name="Fries", price=15.0, tax_rate=0.17, preparation_time_min=10)
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
    category = MenuCategory(location_id=location.id, name="Food", sort_order=0)
    db.add(category)
    await db.flush()
    burger = MenuItem(category_id=category.id, name="Burger", price=45.0, tax_rate=0.17, preparation_time_min=15)
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
async def test_payment_completes_order(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    category = MenuCategory(location_id=location.id, name="Food", sort_order=0)
    db.add(category)
    await db.flush()
    item = MenuItem(category_id=category.id, name="Salad", price=30.0, tax_rate=0.17, preparation_time_min=5)
    db.add(item)
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}

    order_resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "takeaway"},
        headers=headers,
    )
    order_id = order_resp.json()["id"]

    await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": item.id, "qty": 1},
        headers=headers,
    )

    # Fetch order total
    order = (await client.get(f"/api/v1/orders/{order_id}", headers=headers)).json()
    total = order["total"]

    # Pay in full
    resp = await client.post(
        "/api/v1/payments",
        json={"orderId": order_id, "method": "card", "amount": total},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "completed"

    # Order should now be paid
    order = (await client.get(f"/api/v1/orders/{order_id}", headers=headers)).json()
    assert order["status"] == "paid"
