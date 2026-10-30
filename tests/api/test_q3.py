import asyncio
from collections.abc import Callable

from httpx import AsyncClient

from conftest import add_item, bearer, create_order, submit_order


async def _jobs_for_order(client: AsyncClient, token: str, location_id: str, order_id: str) -> list[dict]:
    jobs = await client.get(f"/locations/{location_id}/print-jobs", headers=bearer(token))
    jobs.raise_for_status()
    return [job for job in jobs.json() if job["orderId"] == order_id]


async def _wait_jobs(
    client: AsyncClient,
    token: str,
    location_id: str,
    order_id: str,
    predicate: Callable[[list[dict]], bool],
    *,
    timeout: float = 8.0,
) -> list[dict]:
    deadline = asyncio.get_event_loop().time() + timeout
    matching: list[dict] = []
    while asyncio.get_event_loop().time() < deadline:
        matching = await _jobs_for_order(client, token, location_id, order_id)
        if predicate(matching):
            return matching
        await asyncio.sleep(0.25)
    raise AssertionError(f"print jobs did not match in time: {matching!r}")


async def test_q3_submit_creates_print_job(
    client: AsyncClient, waiter_a: dict, owner_a: dict, catalog: dict
) -> None:
    token = waiter_a["token"]
    location_id = owner_a["locationId"]
    order = await create_order(client, token, location_id)
    first = await add_item(client, token, order["id"], catalog["burgerId"])
    submitted = await submit_order(client, token, order["id"])

    matching = await _wait_jobs(
        client, owner_a["token"], location_id, submitted["id"], lambda jobs: len(jobs) == 1
    )
    assert matching[0]["itemId"] == first["id"]

    retry = await client.post(f"/orders/{submitted['id']}/submit", headers=bearer(token))
    assert retry.status_code == 400
    await asyncio.sleep(0.5)
    assert len(await _jobs_for_order(client, owner_a["token"], location_id, submitted["id"])) == 1

    second = await add_item(client, token, submitted["id"], catalog["burgerId"])
    matching = await _wait_jobs(
        client, owner_a["token"], location_id, submitted["id"], lambda jobs: len(jobs) == 2
    )
    assert {job["itemId"] for job in matching} == {first["id"], second["id"]}

    course_two = await add_item(
        client, token, submitted["id"], catalog["burgerId"], fire_course=2
    )
    await asyncio.sleep(0.5)
    assert len(await _jobs_for_order(client, owner_a["token"], location_id, submitted["id"])) == 2

    fired = await client.post(
        f"/orders/{submitted['id']}/fire-course",
        headers=bearer(token),
        json={"course": 2},
    )
    fired.raise_for_status()
    matching = await _wait_jobs(
        client, owner_a["token"], location_id, submitted["id"], lambda jobs: len(jobs) == 3
    )
    assert {job["itemId"] for job in matching} == {first["id"], second["id"], course_two["id"]}

    again = await client.post(
        f"/orders/{submitted['id']}/fire-course",
        headers=bearer(token),
        json={"course": 2},
    )
    assert again.status_code == 400
    await asyncio.sleep(0.5)
    assert len(await _jobs_for_order(client, owner_a["token"], location_id, submitted["id"])) == 3
