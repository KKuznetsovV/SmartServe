import pytest
import websockets
from httpx import AsyncClient

from conftest import API_BASE_URL, add_item, create_order, submit_order


def _ws_url(location_id: str) -> str:
    http_base = API_BASE_URL.rstrip("/")
    if http_base.startswith("https://"):
        return "wss://" + http_base.removeprefix("https://") + f"/ws/{location_id}"
    return "ws://" + http_base.removeprefix("http://") + f"/ws/{location_id}"


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
