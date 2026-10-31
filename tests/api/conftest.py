"""Black-box fixtures against a running gateway (`python scripts/demo.py --reset`)."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
import pytest_asyncio

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080/api/v1")
WEB_BASE_URL = os.environ.get("WEB_BASE_URL", "http://localhost:3000")
PRINTING_BASE_URL = os.environ.get("PRINTING_BASE_URL", "http://localhost:8080/api/v1")
REPORTING_BASE_URL = os.environ.get("REPORTING_BASE_URL", "http://localhost:8080/api/v1")

OWNER_A_EMAIL = "owner@demo.com"
OWNER_A_PASSWORD = "demo1234"
MANAGER_A_EMAIL = "manager@demo.com"
MANAGER_A_PASSWORD = "demo1234"
OWNER_B_EMAIL = "owner@other.com"
OWNER_B_PASSWORD = "other1234"
WAITER_PIN = "1234"
KITCHEN_PIN = "5678"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0) as c:
        yield c


_TOKEN_CACHE: dict[str, str] = {}


async def _login(client: httpx.AsyncClient, email: str, password: str) -> str:
    cached = _TOKEN_CACHE.get(email)
    if cached:
        return cached
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    if resp.status_code == 429:
        await asyncio.sleep(7)
        resp = await client.post("/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    token = resp.json()["accessToken"]
    _TOKEN_CACHE[email] = token
    return token


async def _me(client: httpx.AsyncClient, token: str) -> dict[str, Any]:
    resp = await client.get("/auth/me", headers=bearer(token))
    resp.raise_for_status()
    return resp.json()


async def _first_location(client: httpx.AsyncClient, token: str, business_id: str) -> dict[str, Any]:
    resp = await client.get(f"/businesses/{business_id}/locations", headers=bearer(token))
    resp.raise_for_status()
    locations = resp.json()
    if not locations:
        raise RuntimeError(f"no locations for business {business_id}; run demo.py with --with-second-tenant")
    return locations[0]


PIN_STAFF_NAMES = {"waiter": "Demo Waiter", "kitchen": "Demo Cook"}


async def _ensure_pos_device(client: httpx.AsyncClient, token: str, location_id: str) -> str:
    cache_key = f"device:{location_id}"
    cached = _TOKEN_CACHE.get(cache_key)
    if cached:
        return cached
    resp = await client.post(
        f"/locations/{location_id}/devices",
        headers=bearer(token),
        json={"name": "API POS", "type": "pos"},
    )
    resp.raise_for_status()
    device_token = resp.json()["token"]
    _TOKEN_CACHE[cache_key] = device_token
    return device_token


def device_headers(device_token: str) -> dict[str, str]:
    return {"X-Device-Token": device_token}


async def _pin_login(
    client: httpx.AsyncClient, location_id: str, role: str, pin: str, *, device_token: str
) -> str:
    cache_key = f"pin:{location_id}:{role}"
    cached = _TOKEN_CACHE.get(cache_key)
    if cached:
        return cached
    staff = await client.get(
        "/auth/pin/staff",
        params={"locationId": location_id},
        headers=device_headers(device_token),
    )
    staff.raise_for_status()
    preferred = PIN_STAFF_NAMES.get(role)
    match = next((row for row in staff.json() if row["name"] == preferred), None)
    if match is None:
        match = next((row for row in staff.json() if row["role"] == role), None)
    if match is None:
        raise RuntimeError(f"no {role} with a PIN at location {location_id}")
    resp = await client.post(
        "/auth/pin",
        json={"locationId": location_id, "userId": match["id"], "pin": pin},
        headers=device_headers(device_token),
    )
    if resp.status_code == 429:
        await asyncio.sleep(7)
        resp = await client.post(
            "/auth/pin",
            json={"locationId": location_id, "userId": match["id"], "pin": pin},
            headers=device_headers(device_token),
        )
    resp.raise_for_status()
    token = resp.json()["accessToken"]
    _TOKEN_CACHE[cache_key] = token
    return token


@pytest_asyncio.fixture
async def owner_a(client: httpx.AsyncClient) -> dict[str, Any]:
    token = await _login(client, OWNER_A_EMAIL, OWNER_A_PASSWORD)
    profile = await _me(client, token)
    location = await _first_location(client, token, profile["businessId"])
    device_token = await _ensure_pos_device(client, token, location["id"])
    await _restore_demo_manager(client, token, location["id"], device_token)
    return {
        **profile,
        "token": token,
        "locationId": location["id"],
        "locationName": location["name"],
        "deviceToken": device_token,
    }


async def _restore_demo_manager(
    client: httpx.AsyncClient, owner_token: str, location_id: str, device_token: str
) -> None:
    staff = await client.get(
        "/auth/pin/staff",
        params={"locationId": location_id},
        headers=device_headers(device_token),
    )
    if staff.status_code != 200:
        return
    manager = next((row for row in staff.json() if row["name"] == "Demo Manager"), None)
    if manager is None or manager["role"] == "manager":
        return
    await client.patch(
        f"/staff/{manager['id']}",
        headers=bearer(owner_token),
        json={"role": "manager", "active": True},
    )


@pytest_asyncio.fixture
async def manager_a(client: httpx.AsyncClient, owner_a: dict[str, Any]) -> dict[str, Any]:
    token = await _login(client, MANAGER_A_EMAIL, MANAGER_A_PASSWORD)
    profile = await _me(client, token)
    return {**profile, "token": token, "locationId": owner_a["locationId"]}


@pytest_asyncio.fixture
async def waiter_a(client: httpx.AsyncClient, owner_a: dict[str, Any]) -> dict[str, Any]:
    token = await _pin_login(
        client, owner_a["locationId"], "waiter", WAITER_PIN, device_token=owner_a["deviceToken"]
    )
    profile = await _me(client, token)
    return {**profile, "token": token, "locationId": owner_a["locationId"]}


@pytest_asyncio.fixture
async def kitchen_a(client: httpx.AsyncClient, owner_a: dict[str, Any]) -> dict[str, Any]:
    token = await _pin_login(
        client, owner_a["locationId"], "kitchen", KITCHEN_PIN, device_token=owner_a["deviceToken"]
    )
    profile = await _me(client, token)
    return {**profile, "token": token, "locationId": owner_a["locationId"]}


@pytest_asyncio.fixture
async def owner_b(client: httpx.AsyncClient) -> dict[str, Any]:
    token = await _login(client, OWNER_B_EMAIL, OWNER_B_PASSWORD)
    profile = await _me(client, token)
    location = await _first_location(client, token, profile["businessId"])
    return {**profile, "token": token, "locationId": location["id"]}


@pytest_asyncio.fixture
async def catalog(client: httpx.AsyncClient, owner_a: dict[str, Any]) -> dict[str, Any]:
    headers = bearer(owner_a["token"])
    cats = await client.get(f"/menu/locations/{owner_a['locationId']}/categories", headers=headers)
    cats.raise_for_status()
    by_name = {row["name"]: row for row in cats.json()}
    items: dict[str, dict[str, Any]] = {}
    for cat in cats.json():
        listed = await client.get(f"/menu/categories/{cat['id']}/items", headers=headers)
        listed.raise_for_status()
        for item in listed.json():
            items[item["name"]] = item
    tables = await client.get(f"/locations/{owner_a['locationId']}/tables", headers=headers)
    tables.raise_for_status()
    if "Cola" not in items or "Burger" not in items:
        raise RuntimeError("demo catalog missing Cola/Burger; run scripts/seed_demo.py")
    if not tables.json():
        raise RuntimeError("demo tables missing; run scripts/seed_demo.py")
    burger = await client.get(f"/menu/items/{items['Burger']['id']}", headers=headers)
    burger.raise_for_status()
    groups = burger.json().get("modifierGroups") or []
    modifier = groups[0]["modifiers"][0] if groups and groups[0].get("modifiers") else None
    return {
        "categories": by_name,
        "items": items,
        "colaId": items["Cola"]["id"],
        "burgerId": items["Burger"]["id"],
        "colaPrice": items["Cola"]["price"],
        "burgerPrice": items["Burger"]["price"],
        "table": tables.json()[0],
        "modifier": modifier,
    }


async def create_order(
    client: httpx.AsyncClient,
    token: str,
    location_id: str,
    *,
    table_id: str | None = None,
    channel: str = "takeaway",
    guest_count: int | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"locationId": location_id, "channel": channel}
    if table_id is not None:
        body["tableId"] = table_id
    if guest_count is not None:
        body["guestCount"] = guest_count
    resp = await client.post("/orders", headers=bearer(token), json=body)
    resp.raise_for_status()
    return resp.json()


async def add_item(
    client: httpx.AsyncClient,
    token: str,
    order_id: str,
    menu_item_id: str,
    *,
    qty: int = 1,
    modifiers: list[dict[str, Any]] | None = None,
    fire_course: int | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"menuItemId": menu_item_id, "qty": qty}
    if modifiers is not None:
        body["modifiers"] = modifiers
    if fire_course is not None:
        body["fireCourse"] = fire_course
    resp = await client.post(f"/orders/{order_id}/items", headers=bearer(token), json=body)
    resp.raise_for_status()
    return resp.json()


async def submit_order(client: httpx.AsyncClient, token: str, order_id: str) -> dict[str, Any]:
    resp = await client.post(f"/orders/{order_id}/submit", headers=bearer(token))
    resp.raise_for_status()
    return resp.json()


async def get_order(client: httpx.AsyncClient, token: str, order_id: str) -> dict[str, Any]:
    resp = await client.get(f"/orders/{order_id}", headers=bearer(token))
    resp.raise_for_status()
    return resp.json()


async def set_item_status(
    client: httpx.AsyncClient,
    token: str,
    order_id: str,
    item_id: str,
    status: str,
) -> dict[str, Any]:
    resp = await client.patch(
        f"/orders/{order_id}/items/{item_id}/status",
        headers=bearer(token),
        json={"status": status},
    )
    resp.raise_for_status()
    return resp.json()
