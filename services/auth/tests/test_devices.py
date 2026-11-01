"""Paired devices: register, list, revoke, and PIN gating."""

from httpx import AsyncClient
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, User


async def _register(client: AsyncClient, token: str, location_id: str, *, name="Front POS", type_="pos"):
    return await client.post(
        f"/api/v1/locations/{location_id}/devices",
        json={"name": name, "type": type_},
        headers={"Authorization": f"Bearer {token}"},
    )


async def test_register_list_and_revoke(client: AsyncClient, manager_user: tuple[User, str], location: Location):
    _, token = manager_user
    created = await _register(client, token, location.id)
    assert created.status_code == 201
    body = created.json()
    assert body["token"]
    assert "tokenHash" not in body
    assert body["type"] == "pos"
    assert body["name"] == "Front POS"

    listed = await client.get(
        f"/api/v1/locations/{location.id}/devices",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert "token" not in rows[0]
    assert rows[0]["id"] == body["id"]

    revoked = await client.post(
        f"/api/v1/devices/{body['id']}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["revokedAt"]


async def test_staff_cannot_register_device(client: AsyncClient, db: AsyncSession, business, location: Location):
    waiter = User(
        business_id=business.id,
        name="Waiter",
        role="waiter",
        pin_hash=hash_password("1234"),
    )
    db.add(waiter)
    await db.flush()
    from smartserve_shared.security import create_access_token

    waiter_token = create_access_token(waiter.id, {"business_id": waiter.business_id, "role": waiter.role})
    resp = await _register(client, waiter_token, location.id)
    assert resp.status_code == 403


async def test_pin_staff_requires_device_token(client: AsyncClient, location: Location):
    resp = await client.get("/api/v1/auth/pin/staff", params={"locationId": location.id})
    assert resp.status_code == 401


async def test_pin_login_requires_device_token(client: AsyncClient, db: AsyncSession, business, location: Location):
    user = User(business_id=business.id, name="Waiter A", role="waiter", pin_hash=hash_password("1234"))
    db.add(user)
    await db.flush()
    resp = await client.post("/api/v1/auth/pin", json={"locationId": location.id, "userId": user.id, "pin": "1234"})
    assert resp.status_code == 401


async def test_pin_with_revoked_device_is_401(
    client: AsyncClient, manager_user: tuple[User, str], location: Location, db: AsyncSession, business
):
    _, token = manager_user
    created = await _register(client, token, location.id)
    device_id = created.json()["id"]
    raw = created.json()["token"]
    await client.post(f"/api/v1/devices/{device_id}/revoke", headers={"Authorization": f"Bearer {token}"})

    user = User(business_id=business.id, name="Waiter A", role="waiter", pin_hash=hash_password("1234"))
    db.add(user)
    await db.flush()

    staff = await client.get(
        "/api/v1/auth/pin/staff",
        params={"locationId": location.id},
        headers={"X-Device-Token": raw},
    )
    assert staff.status_code == 401


async def test_pin_staff_updates_last_seen(client: AsyncClient, manager_user: tuple[User, str], location: Location):
    _, token = manager_user
    created = await _register(client, token, location.id)
    raw = created.json()["token"]
    device_id = created.json()["id"]
    assert created.json()["lastSeenAt"] is None

    staff = await client.get(
        "/api/v1/auth/pin/staff",
        params={"locationId": location.id},
        headers={"X-Device-Token": raw},
    )
    assert staff.status_code == 200

    listed = await client.get(
        f"/api/v1/locations/{location.id}/devices",
        headers={"Authorization": f"Bearer {token}"},
    )
    row = next(r for r in listed.json() if r["id"] == device_id)
    assert row["lastSeenAt"]


async def test_current_device_from_token(client: AsyncClient, manager_user: tuple[User, str], location: Location):
    _, token = manager_user
    created = await _register(client, token, location.id, type_="kds")
    raw = created.json()["token"]
    missing = await client.get("/api/v1/devices/current")
    assert missing.status_code == 401
    current = await client.get("/api/v1/devices/current", headers={"X-Device-Token": raw})
    assert current.status_code == 200
    assert current.json()["id"] == created.json()["id"]
    assert current.json()["type"] == "kds"
    assert current.json()["locationId"] == location.id


async def test_waiter_can_read_own_location_and_current_device(
    client: AsyncClient,
    db: AsyncSession,
    business,
    manager_user: tuple[User, str],
    location: Location,
):
    waiter = User(
        business_id=business.id,
        name="Waiter",
        role="waiter",
        pin_hash=hash_password("1234"),
    )
    db.add(waiter)
    await db.flush()
    waiter_token = create_access_token(waiter.id, {"business_id": waiter.business_id, "role": waiter.role})
    _, manager_token = manager_user
    created = await _register(client, manager_token, location.id)
    raw = created.json()["token"]

    got = await client.get(
        f"/api/v1/locations/{location.id}",
        headers={"Authorization": f"Bearer {waiter_token}"},
    )
    assert got.status_code == 200, got.text
    assert got.json()["id"] == location.id

    current = await client.get("/api/v1/devices/current", headers={"X-Device-Token": raw})
    assert current.status_code == 200
    assert current.json()["locationId"] == location.id

    listed = await client.get(
        f"/api/v1/locations/{location.id}/devices",
        headers={"Authorization": f"Bearer {waiter_token}"},
    )
    assert listed.status_code == 403
