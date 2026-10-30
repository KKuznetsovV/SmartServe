import asyncio

from httpx import AsyncClient

from conftest import add_item, bearer, create_order, get_order, submit_order


async def test_q5_payment_rules(client: AsyncClient, waiter_a: dict, catalog: dict) -> None:
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
    assert pay_cancelled.status_code == 409

    empty = await create_order(client, waiter_a["token"], location_id)
    pay_empty = await client.post(
        "/payments",
        headers=headers,
        json={"orderId": empty["id"], "method": "cash", "amount": 1},
    )
    assert pay_empty.status_code == 409

    unsent = await create_order(client, waiter_a["token"], location_id)
    await add_item(client, waiter_a["token"], unsent["id"], catalog["colaId"])
    pay_unsent = await client.post(
        "/payments",
        headers=headers,
        json={"orderId": unsent["id"], "method": "cash", "amount": 1},
    )
    assert pay_unsent.status_code == 409

    over = await create_order(client, waiter_a["token"], location_id)
    await add_item(client, waiter_a["token"], over["id"], catalog["colaId"])
    submitted = await submit_order(client, waiter_a["token"], over["id"])
    pay_over = await client.post(
        "/payments",
        headers=headers,
        json={"orderId": submitted["id"], "method": "card", "amount": submitted["total"] + 50},
    )
    assert pay_over.status_code == 409
    assert pay_over.json()["detail"]


async def test_q5_idempotency_key_charges_once(client: AsyncClient, waiter_a: dict, catalog: dict) -> None:
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
    submitted = await submit_order(client, waiter_a["token"], order["id"])
    headers = {**bearer(waiter_a["token"]), "Idempotency-Key": f"q5-{submitted['id']}"}
    body = {"orderId": submitted["id"], "method": "card", "amount": submitted["total"]}
    first = await client.post("/payments", headers=headers, json=body)
    second = await client.post("/payments", headers=headers, json=body)
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    listed = await client.get(f"/orders/{submitted['id']}/payments", headers=bearer(waiter_a["token"]))
    listed.raise_for_status()
    assert len(listed.json()) == 1


async def test_q5_concurrent_full_payments(client: AsyncClient, waiter_a: dict, catalog: dict) -> None:
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    await add_item(client, waiter_a["token"], order["id"], catalog["burgerId"])
    submitted = await submit_order(client, waiter_a["token"], order["id"])
    headers = bearer(waiter_a["token"])
    body = {"orderId": submitted["id"], "method": "card", "amount": submitted["total"]}
    first, second = await asyncio.gather(
        client.post("/payments", headers=headers, json=body),
        client.post("/payments", headers=headers, json=body),
    )
    statuses = sorted([first.status_code, second.status_code])
    assert statuses == [201, 409]
    listed = await client.get(f"/orders/{submitted['id']}/payments", headers=headers)
    listed.raise_for_status()
    assert len(listed.json()) == 1


async def test_q5_refund_moves_order_back_to_served(
    client: AsyncClient, waiter_a: dict, manager_a: dict, catalog: dict
) -> None:
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
    submitted = await submit_order(client, waiter_a["token"], order["id"])
    paid = await client.post(
        "/payments",
        headers=bearer(waiter_a["token"]),
        json={"orderId": submitted["id"], "method": "card", "amount": submitted["total"]},
    )
    paid.raise_for_status()
    refunded = await client.post(
        f"/payments/{paid.json()['id']}/refund",
        headers=bearer(manager_a["token"]),
        json={"managerUserId": manager_a["id"], "pin": "2222", "reason": "guest changed mind"},
    )
    assert refunded.status_code == 200
    for _ in range(20):
        refreshed = await get_order(client, waiter_a["token"], submitted["id"])
        if refreshed["status"] == "served":
            break
        await asyncio.sleep(0.25)
    else:
        refreshed = await get_order(client, waiter_a["token"], submitted["id"])
    assert refreshed["status"] == "served"
