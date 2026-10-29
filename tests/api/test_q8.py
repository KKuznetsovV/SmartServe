import pytest
from httpx import AsyncClient

from conftest import bearer


@pytest.mark.xfail(strict=True, reason="Q8")
async def test_q8_catalog_validation(client: AsyncClient, owner_a: dict) -> None:
    headers = bearer(owner_a["token"])
    location_id = owner_a["locationId"]
    parent = await client.post(
        "/menu/categories",
        headers=headers,
        json={"locationId": location_id, "name": "Q8 parent"},
    )
    parent.raise_for_status()
    child = await client.post(
        "/menu/categories",
        headers=headers,
        json={"locationId": location_id, "name": "Q8 child", "parentId": parent.json()["id"]},
    )
    child.raise_for_status()

    negative = await client.post(
        "/menu/items",
        headers=headers,
        json={"categoryId": parent.json()["id"], "name": "Q8 negative", "price": -1},
    )
    assert negative.status_code == 422

    cycle = await client.patch(
        f"/menu/categories/{parent.json()['id']}",
        headers=headers,
        json={"parentId": child.json()["id"]},
    )
    assert cycle.status_code == 400

    reorder = await client.post(
        f"/menu/locations/{location_id}/categories/reorder",
        headers=headers,
        json={},
    )
    assert reorder.status_code == 422
