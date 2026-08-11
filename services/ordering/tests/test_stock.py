"""Cross-domain test: an out-of-stock menu item (catalog) blocks adding to an order (ordering).

Pure stock CRUD tests live in services/catalog/tests/test_stock.py; this test exercises
ordering's OrderService.add_item, which reads the shared MenuItem.in_stock column directly.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, MenuItem, User


@pytest.mark.asyncio
async def test_out_of_stock_blocks_order_add(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    menu_item: MenuItem,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    menu_item.in_stock = False
    await db.flush()

    resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
        headers=headers,
    )
    order_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": menu_item.id, "qty": 1},
        headers=headers,
    )
    assert resp.status_code == 409
    assert "out of stock" in resp.json()["detail"].lower()
