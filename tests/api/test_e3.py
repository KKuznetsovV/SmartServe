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
    location_id = owner_a["locationId"]
    suffix = uuid.uuid4().hex[:8]
    created = await client.post(
        "/menu/categories",
        headers=headers,
        json={"locationId": location_id, "name": f"E3 fail cat {suffix}"},
    )
    created.raise_for_status()
    item = await client.post(
        "/menu/items",
        headers=headers,
        json={"categoryId": created.json()["id"], "name": f"E3 fail item {suffix}", "price": 10},
    )
    item.raise_for_status()
    item_id = item.json()["id"]

    group = await client.post(
        "/menu/modifier-groups",
        headers=headers,
        json={"itemId": item_id, "name": f"E3 group {suffix}"},
    )
    group.raise_for_status()

    trashed = await client.delete(f"/menu/items/{item_id}", headers=headers)
    assert trashed.status_code == 204

    deleted = await client.delete(f"/menu/items/{item_id}/permanent", headers=headers)
    assert deleted.status_code // 100 != 2
    assert deleted.status_code == 409

    trash = await client.get(f"/menu/locations/{location_id}/trash", headers=headers)
    trash.raise_for_status()
    assert any(row["id"] == item_id for row in trash.json())
