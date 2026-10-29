import asyncio
import json

import httpx
import pytest
from httpx import AsyncClient

from conftest import REPORTING_BASE_URL, add_item, bearer, create_order, submit_order


@pytest.mark.xfail(strict=True, reason="S6")
async def test_s6_audit_log_is_tenant_scoped(
    client: AsyncClient, waiter_a: dict, owner_a: dict, owner_b: dict, catalog: dict
) -> None:
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
    submitted = await submit_order(client, waiter_a["token"], order["id"])
    await asyncio.sleep(1)

    resp = await client.get("/events", headers=bearer(owner_b["token"]))
    if resp.status_code == 404:
        async with httpx.AsyncClient(base_url=REPORTING_BASE_URL, timeout=30.0) as reporting:
            resp = await reporting.get("/events", headers=bearer(owner_b["token"]))
    assert resp.status_code == 200
    events = resp.json()
    assert events
    leaked = []
    for row in events:
        payload_raw = row.get("payload") or ""
        try:
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            continue
        if payload.get("orderId") == submitted["id"] or payload.get("locationId") == owner_a["locationId"]:
            leaked.append(row)
    assert leaked == []
