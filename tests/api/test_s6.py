import asyncio
import json
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from conftest import add_item, bearer, create_order, submit_order


def _payload(row: dict) -> dict:
    payload_raw = row.get("payload") or ""
    if isinstance(payload_raw, str):
        try:
            parsed = json.loads(payload_raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return payload_raw if isinstance(payload_raw, dict) else {}


async def _audit_events(client: AsyncClient, token: str, **params) -> list[dict]:
    resp = await client.get("/audit/events", headers=bearer(token), params=params or None)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_s6_audit_log_is_tenant_scoped(
    client: AsyncClient, waiter_a: dict, owner_a: dict, owner_b: dict, catalog: dict
) -> None:
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
    submitted = await submit_order(client, waiter_a["token"], order["id"])
    pay = await client.post(
        "/payments",
        headers=bearer(waiter_a["token"]),
        json={"orderId": submitted["id"], "method": "cash", "amount": submitted["total"]},
    )
    assert pay.status_code == 201, pay.text

    a_payments: list[dict] = []
    for _ in range(20):
        a_payments = await _audit_events(client, owner_a["token"], routing_key="payment.completed")
        if any(_payload(row).get("orderId") == submitted["id"] for row in a_payments):
            break
        await asyncio.sleep(0.5)
    assert any(_payload(row).get("orderId") == submitted["id"] for row in a_payments)

    a_events = await _audit_events(client, owner_a["token"])
    a_order_ids = {_payload(row).get("orderId") for row in a_events}
    assert submitted["id"] in a_order_ids

    b_events = await _audit_events(client, owner_b["token"])
    leaked = []
    for row in b_events:
        payload = _payload(row)
        if (
            payload.get("orderId") == submitted["id"]
            or payload.get("locationId") == owner_a["locationId"]
            or payload.get("businessId") == owner_a["businessId"]
        ):
            leaked.append(row)
    assert leaked == []

    b_payments = await _audit_events(client, owner_b["token"], routing_key="payment.completed")
    assert all(_payload(row).get("orderId") != submitted["id"] for row in b_payments)

    b_ai = await _audit_events(client, owner_b["token"], routing_key="ai.action_executed")
    for row in b_ai:
        payload = _payload(row)
        assert payload.get("locationId") != owner_a["locationId"]
        assert payload.get("businessId") != owner_a["businessId"]

    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    none_since = await _audit_events(client, owner_a["token"], since=future)
    assert none_since == []
