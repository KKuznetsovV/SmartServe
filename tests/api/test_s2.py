import pytest
from httpx import AsyncClient

from conftest import bearer


async def test_s2_manager_role_hierarchy(
    client: AsyncClient, manager_a: dict, waiter_a: dict, owner_a: dict
) -> None:
    headers = bearer(manager_a["token"])
    owner_headers = bearer(owner_a["token"])
    try:
        own_role = await client.patch(
            f"/staff/{manager_a['id']}",
            headers=headers,
            json={"role": "waiter"},
        )
        assert own_role.status_code in {400, 403}

        assign_owner = await client.patch(
            f"/staff/{waiter_a['id']}",
            headers=headers,
            json={"role": "owner"},
        )
        assert assign_owner.status_code in {400, 403}

        deactivate_owner = await client.patch(
            f"/staff/{owner_a['id']}",
            headers=headers,
            json={"active": False},
        )
        assert deactivate_owner.status_code in {400, 403}

        superadmin = await client.patch(
            f"/staff/{waiter_a['id']}",
            headers=headers,
            json={"role": "superadmin"},
        )
        assert superadmin.status_code == 422
    finally:
        await client.patch(
            f"/staff/{manager_a['id']}",
            headers=owner_headers,
            json={"role": "manager", "active": True},
        )
        await client.patch(
            f"/staff/{waiter_a['id']}",
            headers=owner_headers,
            json={"role": "waiter", "active": True},
        )
        await client.patch(
            f"/staff/{owner_a['id']}",
            headers=owner_headers,
            json={"role": "owner", "active": True},
        )
