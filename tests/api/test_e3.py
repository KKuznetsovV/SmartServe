import asyncio
import uuid

from httpx import AsyncClient

from conftest import bearer


async def test_e3_delete_category_with_items_is_409(
    client: AsyncClient, owner_a: dict, catalog: dict
) -> None:
    headers = bearer(owner_a["token"])
    location_id = owner_a["locationId"]
    created = await client.post(
        "/menu/categories",
        headers=headers,
        json={"locationId": location_id, "name": f"E3 category {uuid.uuid4().hex[:8]}"},
    )
    created.raise_for_status()
    category_id = created.json()["id"]
    item = await client.post(
        "/menu/items",
        headers=headers,
        json={"categoryId": category_id, "name": f"E3 item {uuid.uuid4().hex[:8]}", "price": 10},
    )
    item.raise_for_status()

    deleted = await client.delete(f"/menu/categories/{category_id}", headers=headers)
    assert deleted.status_code == 409

    cats = await client.get(f"/menu/locations/{location_id}/categories", headers=headers)
    cats.raise_for_status()
    assert any(row["id"] == category_id for row in cats.json())


async def test_e3_commit_failure_is_not_2xx(client: AsyncClient, owner_a: dict) -> None:
    headers = bearer(owner_a["token"])
    code = f"E3{uuid.uuid4().hex[:10]}"
    body = {
        "businessId": owner_a["businessId"],
        "code": code,
        "name": "E3 unique",
        "type": "percent",
        "value": 5,
    }
    first, second = await asyncio.gather(
        client.post("/discounts", headers=headers, json=body),
        client.post("/discounts", headers=headers, json=body),
    )
    statuses = {first.status_code, second.status_code}
    assert 201 in statuses
    for resp in (first, second):
        if resp.status_code != 201:
            assert resp.status_code // 100 != 2
            assert resp.status_code == 409
