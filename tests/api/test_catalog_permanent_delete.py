import uuid

from httpx import AsyncClient

from conftest import bearer


async def test_trashed_item_with_modifier_group_can_be_permanently_deleted(
    client: AsyncClient, owner_a: dict
) -> None:
    headers = bearer(owner_a["token"])
    location_id = owner_a["locationId"]
    suffix = uuid.uuid4().hex[:8]
    created = await client.post(
        "/menu/categories",
        headers=headers,
        json={"locationId": location_id, "name": f"Cascade cat {suffix}"},
    )
    created.raise_for_status()
    item = await client.post(
        "/menu/items",
        headers=headers,
        json={"categoryId": created.json()["id"], "name": f"Cascade item {suffix}", "price": 10},
    )
    item.raise_for_status()
    item_id = item.json()["id"]

    group = await client.post(
        "/menu/modifier-groups",
        headers=headers,
        json={"itemId": item_id, "name": f"Cascade group {suffix}"},
    )
    group.raise_for_status()
    group_id = group.json()["id"]

    trashed = await client.delete(f"/menu/items/{item_id}", headers=headers)
    assert trashed.status_code == 204

    deleted = await client.delete(f"/menu/items/{item_id}/permanent", headers=headers)
    assert deleted.status_code == 204

    trash = await client.get(f"/menu/locations/{location_id}/trash", headers=headers)
    trash.raise_for_status()
    assert all(row["id"] != item_id for row in trash.json())

    leftover = await client.patch(
        f"/menu/modifier-groups/{group_id}",
        headers=headers,
        json={"name": "gone"},
    )
    assert leftover.status_code == 404
