import asyncio

import httpx
import pytest
from httpx import AsyncClient

from conftest import PRINTING_BASE_URL, add_item, bearer, create_order, submit_order


@pytest.mark.xfail(strict=True, reason="Q3")
async def test_q3_submit_creates_print_job(
    client: AsyncClient, waiter_a: dict, owner_a: dict, catalog: dict
) -> None:
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    await add_item(client, waiter_a["token"], order["id"], catalog["burgerId"])
    submitted = await submit_order(client, waiter_a["token"], order["id"])
    await asyncio.sleep(1)

    headers = bearer(owner_a["token"])
    location_id = owner_a["locationId"]
    jobs = await client.get(f"/locations/{location_id}/print-jobs", headers=headers)
    if jobs.status_code == 404:
        async with httpx.AsyncClient(base_url=PRINTING_BASE_URL, timeout=30.0) as printing:
            jobs = await printing.get(f"/locations/{location_id}/print-jobs", headers=headers)
    jobs.raise_for_status()
    matching = [job for job in jobs.json() if job["orderId"] == submitted["id"]]
    assert matching
