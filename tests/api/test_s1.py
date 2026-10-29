import pytest
from httpx import AsyncClient

from conftest import add_item, bearer, create_order, submit_order


@pytest.mark.xfail(strict=True, reason="S1")
async def test_s1_business_b_cannot_reach_a_resources(
    client: AsyncClient, waiter_a: dict, owner_a: dict, owner_b: dict, catalog: dict
) -> None:
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
    submitted = await submit_order(client, waiter_a["token"], order["id"])

    b = bearer(owner_b["token"])
    a_location = owner_a["locationId"]

    payment = await client.post(
        "/payments",
        headers=b,
        json={"orderId": submitted["id"], "method": "cash", "amount": 1},
    )
    assert payment.status_code == 404

    listed = await client.get(f"/orders/{submitted['id']}/payments", headers=b)
    assert listed.status_code == 404

    shifts = await client.get(f"/locations/{a_location}/shifts", headers=b)
    assert shifts.status_code == 404

    opened = await client.post(
        f"/locations/{a_location}/shifts/open",
        headers=b,
        json={"openingCash": 0},
    )
    assert opened.status_code == 404

    printer = await client.post(
        "/printers",
        headers=b,
        json={"locationId": a_location, "name": "B on A", "type": "kitchen"},
    )
    assert printer.status_code == 404

    printers = await client.get(f"/locations/{a_location}/printers", headers=b)
    assert printers.status_code == 404

    routes = await client.get(f"/locations/{a_location}/printer-routes", headers=b)
    assert routes.status_code == 404
