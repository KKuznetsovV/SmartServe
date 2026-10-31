import websockets
from httpx import AsyncClient

from conftest import API_BASE_URL, add_item, bearer, create_order, device_headers, submit_order


def _ws_url(location_id: str, *, ticket: str | None = None, device_token: str | None = None) -> str:
    http_base = API_BASE_URL.rstrip("/")
    scheme = "wss://" if http_base.startswith("https://") else "ws://"
    prefix = "https://" if http_base.startswith("https://") else "http://"
    url = scheme + http_base.removeprefix(prefix) + f"/ws/{location_id}"
    if ticket:
        return url + f"?ticket={ticket}"
    if device_token:
        return url + f"?deviceToken={device_token}"
    return url


async def issue_ws_ticket(client: AsyncClient, token: str, location_id: str) -> str:
    resp = await client.post(
        "/ws/ticket", json={"locationId": location_id}, headers={"Authorization": f"Bearer {token}"}
    )
    resp.raise_for_status()
    return resp.json()["ticket"]


async def connect_location_ws(client: AsyncClient, token: str, location_id: str):
    ticket = await issue_ws_ticket(client, token, location_id)
    return await websockets.connect(_ws_url(location_id, ticket=ticket), open_timeout=10)


async def _register_display(client: AsyncClient, token: str, location_id: str) -> tuple[str, str]:
    resp = await client.post(
        f"/locations/{location_id}/devices",
        headers=bearer(token),
        json={"name": "Front display", "type": "display"},
    )
    resp.raise_for_status()
    body = resp.json()
    return body["id"], body["token"]


async def test_s4_anonymous_socket_is_rejected(waiter_a: dict) -> None:
    connected = False
    try:
        async with websockets.connect(_ws_url(waiter_a["locationId"]), open_timeout=5):
            connected = True
    except Exception:
        connected = False
    assert not connected


async def test_s4_reused_ticket_is_rejected(client: AsyncClient, waiter_a: dict) -> None:
    ticket = await issue_ws_ticket(client, waiter_a["token"], waiter_a["locationId"])
    first = await websockets.connect(_ws_url(waiter_a["locationId"], ticket=ticket), open_timeout=10)
    await first.close()
    reused = False
    try:
        async with websockets.connect(_ws_url(waiter_a["locationId"], ticket=ticket), open_timeout=5):
            reused = True
    except Exception:
        reused = False
    assert not reused


async def test_s4_revoked_device_gets_401(client: AsyncClient, owner_a: dict) -> None:
    device_id, raw = await _register_display(client, owner_a["token"], owner_a["locationId"])
    revoke = await client.post(f"/devices/{device_id}/revoke", headers=bearer(owner_a["token"]))
    revoke.raise_for_status()
    display = await client.get("/public/display/orders", headers=device_headers(raw))
    assert display.status_code == 401


async def test_s4_display_payload_has_exactly_three_fields(
    client: AsyncClient, owner_a: dict, waiter_a: dict, catalog: dict
) -> None:
    _device_id, raw = await _register_display(client, owner_a["token"], owner_a["locationId"])
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
    await submit_order(client, waiter_a["token"], order["id"])

    missing = await client.get("/public/display/orders")
    assert missing.status_code == 401

    gone = await client.get(f"/public/locations/{waiter_a['locationId']}/orders")
    assert gone.status_code == 404

    display = await client.get("/public/display/orders", headers=device_headers(raw))
    display.raise_for_status()
    rows = display.json()
    assert rows
    for row in rows:
        assert set(row.keys()) == {"orderNumber", "status", "updatedAt"}
