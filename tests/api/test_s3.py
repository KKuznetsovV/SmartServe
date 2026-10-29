import pytest
from httpx import AsyncClient

from conftest import add_item, bearer, create_order, get_order


@pytest.mark.xfail(strict=True, reason="S3")
async def test_s3_server_side_pricing_and_qty(
    client: AsyncClient, waiter_a: dict, catalog: dict
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
