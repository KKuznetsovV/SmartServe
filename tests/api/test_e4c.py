import uuid

from httpx import AsyncClient

from conftest import add_item, bearer, create_order, get_order


async def test_e4c_trashed_item_on_old_order_can_be_permanently_deleted(
    client: AsyncClient, owner_a: dict, waiter_a: dict
) -> None:
    headers = bearer(owner_a["token"])
    location_id = owner_a["locationId"]
    suffix = uuid.uuid4().hex[:8]
    name = f"E4c snapshot {suffix}"
    price = 12.5

    category = await client.post(
        "/menu/categories",
        headers=headers,
        json={"locationId": location_id, "name": f"E4c cat {suffix}"},
    )
    category.raise_for_status()
    item = await client.post(
        "/menu/items",
        headers=headers,
        json={"categoryId": category.json()["id"], "name": name, "price": price},
    )
    item.raise_for_status()
    item_id = item.json()["id"]

    order = await create_order(client, waiter_a["token"], location_id)
    await add_item(client, waiter_a["token"], order["id"], item_id)

    trashed = await client.delete(f"/menu/items/{item_id}", headers=headers)
    assert trashed.status_code == 204

    deleted = await client.delete(f"/menu/items/{item_id}/permanent", headers=headers)
    assert deleted.status_code == 204

    refreshed = await get_order(client, waiter_a["token"], order["id"])
    assert refreshed["items"]
    line = next(row for row in refreshed["items"] if row["menuItemId"] == item_id)
    assert line["menuItemName"] == name
    assert line["unitPrice"] == price
