"""S5: PIN lockout (423) and rate limits keyed on the real client IP."""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path

from httpx import AsyncClient

from conftest import add_item, bearer, create_order, device_headers, submit_order

REPO_ROOT = Path(__file__).resolve().parents[2]


async def _staff_with_pin(client: AsyncClient, owner: dict, *, name: str, role: str, pin: str) -> str:
    resp = await client.post(
        "/staff",
        headers=bearer(owner["token"]),
        json={"name": name, "role": role, "pin": pin},
    )
    resp.raise_for_status()
    return resp.json()["id"]


async def test_s5_five_wrong_pins_then_correct_pin_still_423(client: AsyncClient, owner_a: dict) -> None:
    user_id = await _staff_with_pin(client, owner_a, name="S5 Lockout Waiter", role="waiter", pin="2468")
    headers = device_headers(owner_a["deviceToken"])
    wrong = {"locationId": owner_a["locationId"], "userId": user_id, "pin": "0000"}
    for i in range(4):
        resp = await client.post("/auth/pin", json=wrong, headers=headers)
        assert resp.status_code == 401, i
    fifth = await client.post("/auth/pin", json=wrong, headers=headers)
    assert fifth.status_code == 423
    assert int(fifth.headers["Retry-After"]) > 0
    correct = await client.post(
        "/auth/pin",
        json={"locationId": owner_a["locationId"], "userId": user_id, "pin": "2468"},
        headers=headers,
    )
    assert correct.status_code == 423


async def test_s5_manager_override_pin_lockout(
    client: AsyncClient, owner_a: dict, waiter_a: dict, catalog: dict
) -> None:
    manager_id = await _staff_with_pin(client, owner_a, name="S5 Lockout Manager", role="manager", pin="9753")
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    item = await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
    await submit_order(client, waiter_a["token"], order["id"])
    headers = bearer(waiter_a["token"])
    wrong = {
        "items": [{"itemId": item["id"]}],
        "override": {"managerUserId": manager_id, "pin": "0000", "reason": "s5 lockout"},
    }
    for i in range(4):
        resp = await client.post(f"/orders/{order['id']}/items/delete", json=wrong, headers=headers)
        assert resp.status_code == 401, i
    fifth = await client.post(f"/orders/{order['id']}/items/delete", json=wrong, headers=headers)
    assert fifth.status_code == 423
    correct = await client.post(
        f"/orders/{order['id']}/items/delete",
        json={
            "items": [{"itemId": item["id"]}],
            "override": {"managerUserId": manager_id, "pin": "9753", "reason": "s5 lockout"},
        },
        headers=headers,
    )
    assert correct.status_code == 423


async def test_s5_gateway_forged_xff_shares_one_bucket(client: AsyncClient) -> None:
    stamp = uuid.uuid4().hex
    ip_a = "198.51.100.10"
    ip_b = "198.51.100.11"
    statuses: list[int] = []
    for i in range(11):
        xff = ip_a if i % 2 == 0 else ip_b
        resp = await client.post(
            "/auth/login",
            json={"email": f"s5-gw-{stamp}-{i}@example.com", "password": "nope"},
            headers={"X-Forwarded-For": xff},
        )
        assert resp.status_code in {401, 429}, i
        statuses.append(resp.status_code)
    assert 429 in statuses
    other = await client.post(
        "/auth/login",
        json={"email": f"s5-gw-{stamp}-other@example.com", "password": "nope"},
        headers={"X-Forwarded-For": ip_b},
    )
    assert other.status_code == 429


async def test_s5_direct_auth_port_ignores_forged_xff() -> None:
    """Hit auth from another compose service so forged X-Forwarded-For is untrusted."""
    stamp = uuid.uuid4().hex
    script = f"""
import json, urllib.error, urllib.request
statuses = []
for i in range(12):
    data = json.dumps({{"email": f"s5-direct-{stamp}-{{i}}@example.com", "password": "nope"}}).encode()
    req = urllib.request.Request(
        "http://auth:8000/api/v1/auth/login",
        data=data,
        method="POST",
        headers={{
            "Content-Type": "application/json",
            "X-Forwarded-For": f"203.0.113.{{i}}",
        }},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            statuses.append(resp.status)
    except urllib.error.HTTPError as exc:
        statuses.append(exc.code)
print(json.dumps(statuses))
"""
    proc = subprocess.run(
        ["docker", "compose", "exec", "-T", "catalog", "python", "-c", script],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    statuses = json.loads(proc.stdout.strip().splitlines()[-1])
    assert 429 in statuses
    assert all(code in {401, 429} for code in statuses)
