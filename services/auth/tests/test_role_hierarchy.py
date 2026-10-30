"""Role hierarchy, PIN/password bounds, and last-owner protection."""

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.modules.staff.service import StaffService


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_unknown_role_is_422(client: AsyncClient, manager_user: tuple[User, str]):
    _, token = manager_user
    resp = await client.post(
        "/api/v1/staff",
        json={"name": "X", "role": "superadmin"},
        headers=_headers(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_manager_cannot_create_owner_or_manager(client: AsyncClient, manager_user: tuple[User, str]):
    _, token = manager_user
    owner = await client.post(
        "/api/v1/staff",
        json={"name": "Peer", "role": "owner"},
        headers=_headers(token),
    )
    assert owner.status_code == 403
    manager = await client.post(
        "/api/v1/staff",
        json={"name": "Peer", "role": "manager"},
        headers=_headers(token),
    )
    assert manager.status_code == 403


@pytest.mark.asyncio
async def test_manager_cannot_assign_owner_or_change_own_role(
    client: AsyncClient,
    manager_user: tuple[User, str],
    owner_user: tuple[User, str],
):
    manager, token = manager_user
    waiter = (
        await client.post(
            "/api/v1/staff",
            json={"name": "Waiter", "role": "waiter"},
            headers=_headers(token),
        )
    ).json()

    assign_owner = await client.patch(
        f"/api/v1/staff/{waiter['id']}",
        json={"role": "owner"},
        headers=_headers(token),
    )
    assert assign_owner.status_code == 403

    own_role = await client.patch(
        f"/api/v1/staff/{manager.id}",
        json={"role": "waiter"},
        headers=_headers(token),
    )
    assert own_role.status_code == 403

    own_active = await client.patch(
        f"/api/v1/staff/{manager.id}",
        json={"active": False},
        headers=_headers(token),
    )
    assert own_active.status_code == 403

    deactivate_owner = await client.patch(
        f"/api/v1/staff/{owner_user[0].id}",
        json={"active": False},
        headers=_headers(token),
    )
    assert deactivate_owner.status_code == 403


@pytest.mark.asyncio
async def test_owner_can_change_another_owner_but_not_the_last(client: AsyncClient, owner_user: tuple[User, str]):
    from smartserve_shared.security import create_access_token

    owner, token = owner_user
    second = await client.post(
        "/api/v1/staff",
        json={"name": "Co-owner", "role": "owner", "password": "password123"},
        headers=_headers(token),
    )
    assert second.status_code == 201
    second_id = second.json()["id"]
    token_b = create_access_token(second_id, {"business_id": owner.business_id, "role": "owner"})

    # Two active owners: B may deactivate A.
    other_off = await client.patch(
        f"/api/v1/staff/{owner.id}",
        json={"active": False},
        headers=_headers(token_b),
    )
    assert other_off.status_code == 200

    # B is now the last active owner and cannot deactivate or demote themselves.
    self_off = await client.patch(
        f"/api/v1/staff/{second_id}",
        json={"active": False},
        headers=_headers(token_b),
    )
    assert self_off.status_code == 403
    self_demote = await client.patch(
        f"/api/v1/staff/{second_id}",
        json={"role": "manager"},
        headers=_headers(token_b),
    )
    assert self_demote.status_code == 403

    # Reactivate A so B can try to remove the last remaining *other* owner — not allowed
    # once A is the only other owner... A is inactive, so demoting inactive A is fine.
    # Recreate an active co-owner from B, then deactivating that co-owner leaves B as last (allowed).
    third = await client.post(
        "/api/v1/staff",
        json={"name": "Co-owner 2", "role": "owner", "password": "password123"},
        headers=_headers(token_b),
    )
    assert third.status_code == 201
    demote_third = await client.patch(
        f"/api/v1/staff/{third.json()['id']}",
        json={"role": "manager"},
        headers=_headers(token_b),
    )
    assert demote_third.status_code == 200


@pytest.mark.asyncio
async def test_last_active_owner_cannot_be_removed(db: AsyncSession, owner_user: tuple[User, str]):
    owner, _ = owner_user
    with pytest.raises(HTTPException) as exc:
        await StaffService(db)._assert_not_last_owner(owner)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_pin_and_password_bounds(client: AsyncClient, manager_user: tuple[User, str]):
    _, token = manager_user
    short_pin = await client.post(
        "/api/v1/staff",
        json={"name": "X", "role": "waiter", "pin": "1"},
        headers=_headers(token),
    )
    assert short_pin.status_code == 422

    letters = await client.post(
        "/api/v1/staff",
        json={"name": "X", "role": "waiter", "pin": "abcd"},
        headers=_headers(token),
    )
    assert letters.status_code == 422

    short_pw = await client.post(
        "/api/v1/staff",
        json={"name": "X", "role": "waiter", "password": "short"},
        headers=_headers(token),
    )
    assert short_pw.status_code == 422

    ok = await client.post(
        "/api/v1/staff",
        json={"name": "X", "role": "waiter", "pin": "123456", "password": "password123"},
        headers=_headers(token),
    )
    assert ok.status_code == 201
