import pytest
from httpx import AsyncClient

from conftest import add_item, bearer, create_order, submit_order


@pytest.mark.xfail(strict=True, reason="Q5")
async def test_q5_payment_rules(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    headers = bearer(waiter_a["token"])
    location_id = waiter_a["locationId"]

    cancelled = await create_order(client, waiter_a["token"], location_id)
    await add_item(client, waiter_a["token"], cancelled["id"], catalog["colaId"])
    await submit_order(client, waiter_a["token"], cancelled["id"])
    cancel_resp = await client.post(f"/orders/{cancelled['id']}/cancel", headers=headers)
    cancel_resp.raise_for_status()
    pay_cancelled = await client.post(
        "/payments",
        headers=headers,
        json={"orderId": cancelled["id"], "method": "cash", "amount": 1},
    )
    assert pay_cancelled.status_code == 400

    empty = await create_order(client, waiter_a["token"], location_id)
    pay_empty = await client.post(
        "/payments",
        headers=headers,
        json={"orderId": empty["id"], "method": "cash", "amount": 1},
    )
    assert pay_empty.status_code == 400

    unsent = await create_order(client, waiter_a["token"], location_id)
    await add_item(client, waiter_a["token"], unsent["id"], catalog["colaId"])
    pay_unsent = await client.post(
        "/payments",
        headers=headers,
        json={"orderId": unsent["id"], "method": "cash", "amount": 1},
    )
    assert pay_unsent.status_code == 400

    over = await create_order(client, waiter_a["token"], location_id)
    await add_item(client, waiter_a["token"], over["id"], catalog["colaId"])
    submitted = await submit_order(client, waiter_a["token"], over["id"])
    pay_over = await client.post(
        "/payments",
        headers=headers,
        json={"orderId": submitted["id"], "method": "card", "amount": submitted["total"] + 50},
    )
    assert pay_over.status_code == 400
