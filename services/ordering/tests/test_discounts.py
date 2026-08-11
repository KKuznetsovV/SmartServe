"""Cross-domain test: applying a discount (catalog) to an order (ordering).

Pure discount CRUD tests live in services/catalog/tests/test_discounts.py; this test
exercises the ordering module's OrderService.apply_discount, which reads the shared
Discount table directly (see docs/microservices-plan.md §4).
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, Location, MenuItem, User


@pytest.mark.asyncio
async def test_apply_discount_to_order(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    location: Location,
    menu_item: MenuItem,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    # Create a 20% discount directly (apps/api no longer exposes /discounts over HTTP —
    # that's owned by services/catalog now)
    from app.db.models import Discount

    discount = Discount(business_id=business.id, code="TWENTY", name="20% Off", type="percent", value=20)
    db.add(discount)
    await db.flush()

    # Create order with one item
    resp = await client.post(
        "/api/v1/orders", json={"locationId": location.id, "channel": "dine_in", "guestCount": 2}, headers=headers
    )
    order_id = resp.json()["id"]
    await client.post(f"/api/v1/orders/{order_id}/items", json={"menuItemId": menu_item.id, "qty": 1}, headers=headers)

    # Apply discount
    resp = await client.post(f"/api/v1/orders/{order_id}/discount", json={"code": "TWENTY"}, headers=headers)
    assert resp.status_code == 200
    order = resp.json()
    assert order["discountAmount"] > 0
    assert order["discountId"] is not None
    expected_discount = round(order["subtotal"] * 0.20, 2)
    assert abs(order["discountAmount"] - expected_discount) < 0.01
    assert order["total"] == pytest.approx(order["subtotal"] + order["taxAmount"] - order["discountAmount"], rel=1e-3)
