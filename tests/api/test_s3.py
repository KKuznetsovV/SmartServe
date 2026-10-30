import uuid

import pytest
from httpx import AsyncClient

from conftest import add_item, bearer, create_order, get_order


async def test_s3_server_side_pricing_and_qty(
    client: AsyncClient, waiter_a: dict, owner_a: dict, catalog: dict
) -> None:
    modifier = catalog["modifier"]
    assert modifier is not None
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    line = await add_item(
        client,
        waiter_a["token"],
        order["id"],
        catalog["burgerId"],
        modifiers=[
            {
                "modifierId": modifier["id"],
                "name": modifier["name"],
                "priceDelta": -68,
            }
        ],
    )
    assert line["unitPrice"] == pytest.approx(catalog["burgerPrice"] + modifier["priceDelta"])
    assert line["modifiers"][0]["name"] == modifier["name"]
    assert line["modifiers"][0]["priceDelta"] == pytest.approx(modifier["priceDelta"])

    negative_qty = await client.post(
        f"/orders/{order['id']}/items",
        headers=bearer(waiter_a["token"]),
        json={"menuItemId": catalog["colaId"], "qty": -3},
    )
    assert negative_qty.status_code == 422

    cola = await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
    discount = await client.post(
        f"/orders/{order['id']}/items/discount",
        headers=bearer(waiter_a["token"]),
        json={
            "items": [{"itemId": cola["id"]}],
            "discountType": "percent",
            "discountValue": -50,
        },
    )
    assert discount.status_code == 422
    refreshed = await get_order(client, waiter_a["token"], order["id"])
    cola_row = next(item for item in refreshed["items"] if item["id"] == cola["id"])
    assert cola_row["discountAmount"] == 0

    other_item_modifier = await client.post(
        f"/orders/{order['id']}/items",
        headers=bearer(waiter_a["token"]),
        json={
            "menuItemId": catalog["colaId"],
            "qty": 1,
            "modifiers": [{"modifierId": modifier["id"]}],
        },
    )
    assert other_item_modifier.status_code == 422

    headers = bearer(owner_a["token"])
    suffix = uuid.uuid4().hex[:8]
    category = await client.post(
        "/menu/categories",
        headers=headers,
        json={"locationId": owner_a["locationId"], "name": f"S3 cat {suffix}"},
    )
    category.raise_for_status()
    item = await client.post(
        "/menu/items",
        headers=headers,
        json={"categoryId": category.json()["id"], "name": f"S3 required {suffix}", "price": 20},
    )
    item.raise_for_status()
    group = await client.post(
        "/menu/modifier-groups",
        headers=headers,
        json={
            "itemId": item.json()["id"],
            "name": f"S3 group {suffix}",
            "required": True,
            "minSelect": 1,
            "maxSelect": 1,
            "modifiers": [{"name": f"S3 option {suffix}", "priceDelta": 2}],
        },
    )
    group.raise_for_status()

    required_order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    missing_required = await client.post(
        f"/orders/{required_order['id']}/items",
        headers=bearer(waiter_a["token"]),
        json={"menuItemId": item.json()["id"], "qty": 1, "modifiers": []},
    )
    assert missing_required.status_code == 422
