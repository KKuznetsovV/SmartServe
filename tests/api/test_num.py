import asyncio
import os

import pytest
from httpx import AsyncClient

from conftest import create_order


@pytest.mark.stack
async def test_num_parallel_creates_are_unique_and_gapless(
    client: AsyncClient, waiter_a: dict, owner_b: dict
) -> None:
    if os.environ.get("SMARTSERVE_STACK") != "1":
        pytest.skip("stack-only: set SMARTSERVE_STACK=1 in the compose API suite")

    location_a = waiter_a["locationId"]
    created = await asyncio.gather(
        *[create_order(client, waiter_a["token"], location_a) for _ in range(30)]
    )
    numbers = sorted(order["orderNumber"] for order in created)
    assert len(set(numbers)) == 30
    assert numbers == list(range(numbers[0], numbers[0] + 30))
    assert len({order["id"] for order in created}) == 30

    other = await create_order(client, owner_b["token"], owner_b["locationId"])
    assert other["orderNumber"] == 1
