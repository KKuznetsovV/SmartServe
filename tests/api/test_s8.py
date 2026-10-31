"""S8: httpOnly refresh cookie, rotation, reuse detection, logout."""

from __future__ import annotations

from httpx import AsyncClient


async def test_s8_refresh_cookie_rotation_reuse_and_logout(client: AsyncClient, owner_a: dict) -> None:
    assert owner_a["token"]
    old = client.cookies.get("refresh_token")
    assert old, "owner login should have set the refresh cookie"

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {owner_a['token']}"})
    assert me.status_code == 200, me.text
    assert "refreshToken" not in me.json()

    first = await client.post("/auth/refresh")
    assert first.status_code == 200, first.text
    body = first.json()
    assert "refreshToken" not in body
    assert body["accessToken"]
    rotated = client.cookies.get("refresh_token")
    assert rotated
    assert rotated != old

    client.cookies.set("refresh_token", old, path="/api/v1/auth")
    reused = await client.post("/auth/refresh")
    assert reused.status_code == 401

    logout = await client.post("/auth/logout")
    assert logout.status_code == 204
    after = await client.post("/auth/refresh")
    assert after.status_code == 401
