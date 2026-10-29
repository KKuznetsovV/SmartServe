import pytest
from httpx import AsyncClient

from conftest import bearer


@pytest.mark.xfail(strict=True, reason="E3")
async def test_e3_delete_category_with_items_is_409(
    client: AsyncClient, owner_a: dict, catalog: dict
) -> None:
    headers = bearer(owner_a["token"])
    location_id = owner_a["locationId"]
    created = await client.post(
        "/menu/categories",
        headers=headers,
        json={"locationId": location_id, "name": "E3 category"},
    )
    created.raise_for_status()
    category_id = created.json()["id"]
    item = await client.post(
        "/menu/items",
        headers=headers,
        json={"categoryId": category_id, "name": "E3 item", "price": 10},
    )
    item.raise_for_status()

    deleted = await client.delete(f"/menu/categories/{category_id}", headers=headers)
    assert deleted.status_code == 409

    cats = await client.get(f"/menu/locations/{location_id}/categories", headers=headers)
    cats.raise_for_status()
    assert any(row["id"] == category_id for row in cats.json())
