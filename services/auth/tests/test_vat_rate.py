import pytest
from httpx import AsyncClient

from app.db.models import Business, Location, User


@pytest.mark.asyncio
async def test_owner_can_set_business_and_location_vat_rate(
    client: AsyncClient,
    business: Business,
    location: Location,
    owner_user: tuple[User, str],
):
    _, token = owner_user
    headers = {"Authorization": f"Bearer {token}"}

    biz = await client.patch(
        f"/api/v1/businesses/{business.id}",
        json={"vatRate": 0.18},
        headers=headers,
    )
    assert biz.status_code == 200
    assert biz.json()["vatRate"] == 0.18

    loc = await client.patch(
        f"/api/v1/locations/{location.id}",
        json={"vatRate": 0},
        headers=headers,
    )
    assert loc.status_code == 200
    assert loc.json()["vatRate"] == 0.0

    cleared = await client.patch(
        f"/api/v1/locations/{location.id}",
        json={"vatRate": None},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["vatRate"] is None
