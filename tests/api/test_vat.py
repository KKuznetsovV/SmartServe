from httpx import AsyncClient

from conftest import add_item, bearer, create_order, get_order


async def test_vat_inclusive_burger_68(client: AsyncClient, waiter_a: dict, catalog: dict) -> None:
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    await add_item(client, waiter_a["token"], order["id"], catalog["burgerId"])
    refreshed = await get_order(client, waiter_a["token"], order["id"])
    assert catalog["burgerPrice"] == 68
    assert refreshed["total"] == 68.00
    assert refreshed["taxAmount"] == 10.37
    assert refreshed["vatRate"] == 0.18


async def test_vat_happy10_on_100(client: AsyncClient, owner_a: dict, waiter_a: dict) -> None:
    headers = bearer(owner_a["token"])
    cat = await client.post(
        "/menu/categories",
        headers=headers,
        json={"locationId": owner_a["locationId"], "name": "VAT 100"},
    )
    cat.raise_for_status()
    item = await client.post(
        "/menu/items",
        headers=headers,
        json={"categoryId": cat.json()["id"], "name": "VAT 100", "price": "100.00"},
    )
    item.raise_for_status()
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    await add_item(client, waiter_a["token"], order["id"], item.json()["id"])
    applied = await client.post(
        f"/orders/{order['id']}/discount",
        headers=bearer(waiter_a["token"]),
        json={"code": "HAPPY10"},
    )
    applied.raise_for_status()
    body = applied.json()
    assert body["total"] == 90.00
    assert body["taxAmount"] == 13.73


async def test_vat_zero_at_location(client: AsyncClient, owner_a: dict, waiter_a: dict, catalog: dict) -> None:
    patched = await client.patch(
        f"/locations/{owner_a['locationId']}",
        headers=bearer(owner_a["token"]),
        json={"vatRate": 0},
    )
    patched.raise_for_status()
    try:
        order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
        await add_item(client, waiter_a["token"], order["id"], catalog["burgerId"])
        refreshed = await get_order(client, waiter_a["token"], order["id"])
        assert refreshed["total"] == 68.00
        assert refreshed["taxAmount"] == 0.00
        assert refreshed["vatRate"] == 0.0
    finally:
        await client.patch(
            f"/locations/{owner_a['locationId']}",
            headers=bearer(owner_a["token"]),
            json={"vatRate": None},
        )


async def test_vat_rate_change_does_not_rewrite_existing_order(
    client: AsyncClient, owner_a: dict, waiter_a: dict, catalog: dict
) -> None:
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    await add_item(client, waiter_a["token"], order["id"], catalog["burgerId"])
    before = await get_order(client, waiter_a["token"], order["id"])
    assert before["total"] == 68.00
    assert before["taxAmount"] == 10.37

    changed = await client.patch(
        f"/businesses/{owner_a['businessId']}",
        headers=bearer(owner_a["token"]),
        json={"vatRate": 0},
    )
    changed.raise_for_status()
    try:
        after = await get_order(client, waiter_a["token"], order["id"])
        assert after["total"] == 68.00
        assert after["taxAmount"] == 10.37
        assert after["vatRate"] == 0.18
    finally:
        await client.patch(
            f"/businesses/{owner_a['businessId']}",
            headers=bearer(owner_a["token"]),
            json={"vatRate": 0.18},
        )
