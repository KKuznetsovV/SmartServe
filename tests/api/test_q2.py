import pytest
from httpx import AsyncClient

from conftest import create_order


@pytest.mark.xfail(strict=True, reason="Q2")
async def test_q2_order_includes_table_name(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    table = catalog["table"]
    order = await create_order(
        client,
        waiter_a["token"],
        waiter_a["locationId"],
        table_id=table["id"],
        channel="dine_in",
        guest_count=2,
    )
    assert order["tableName"]
    assert order["tableName"] == table["name"]
