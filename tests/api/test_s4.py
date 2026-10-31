import pytest
import websockets
from httpx import AsyncClient

from conftest import API_BASE_URL, add_item, create_order, submit_order


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
    resp = await client.post("/ws/ticket", json={"locationId": location_id}, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json()["ticket"]


async def connect_location_ws(client: AsyncClient, token: str, location_id: str):
    ticket = await issue_ws_ticket(client, token, location_id)
    return await websockets.connect(_ws_url(location_id, ticket=ticket), open_timeout=10)


@pytest.mark.xfail(strict=True, reason="S4")
async def test_s4_anonymous_ws_display_and_pin_staff(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    location_id = waiter_a["locationId"]
    order = await create_order(client, waiter_a["token"], location_id)
    await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
    await submit_order(client, waiter_a["token"], order["id"])

    connected = False
    try:
        async with websockets.connect(_ws_url(location_id), open_timeout=5):
            connected = True
    except Exception:
        connected = False
    assert not connected

    display = await client.get(f"/public/locations/{location_id}/orders")
    display.raise_for_status()
    allowed = {"number", "status"}
    for row in display.json():
        assert set(row.keys()) <= allowed

    pin_staff = await client.get("/auth/pin/staff", params={"locationId": location_id})
    assert pin_staff.status_code == 401
