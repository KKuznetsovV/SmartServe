"""S8: httpOnly refresh cookie, rotation, reuse detection, logout."""

from __future__ import annotations

import os

import httpx

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080/api/v1")
OWNER_EMAIL = "owner@demo.com"
OWNER_PASSWORD = "demo1234"


async def test_s8_refresh_cookie_rotation_reuse_and_logout() -> None:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0) as client:
        login = await client.post("/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
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

        login = await client.post("/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
        assert login.status_code == 200
        logout = await client.post("/auth/logout")
        assert logout.status_code == 204
        after = await client.post("/auth/refresh")
        assert after.status_code == 401
