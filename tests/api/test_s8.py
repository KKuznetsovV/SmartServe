"""S8: httpOnly refresh cookie, rotation, reuse detection, logout."""

from __future__ import annotations

import asyncio

import httpx

from conftest import API_BASE_URL, OWNER_A_EMAIL, OWNER_A_PASSWORD


async def _login_with_cookie(client: httpx.AsyncClient) -> httpx.Response:
    last = None
    for _ in range(5):
        last = await client.post("/auth/login", json={"email": OWNER_A_EMAIL, "password": OWNER_A_PASSWORD})
        if last.status_code != 429:
            return last
        await asyncio.sleep(int(last.headers.get("Retry-After", "60")) + 1)
    return last


async def test_s8_refresh_cookie_rotation_reuse_and_logout() -> None:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0) as client:
        login = await _login_with_cookie(client)
        assert login.status_code == 200, login.text
        body = login.json()
        assert "refreshToken" not in body
        assert body["accessToken"]
        old = client.cookies.get("refresh_token")
        assert old

        first = await client.post("/auth/refresh")
        assert first.status_code == 200, first.text
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
