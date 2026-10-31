import pytest
from httpx import AsyncClient

from app.db.models import Location, User


@pytest.mark.asyncio
async def test_location_cutoff_defaults_and_is_editable(
    client: AsyncClient,
    location: Location,
    owner_user: tuple[User, str],
):
    _, token = owner_user
    headers = {"Authorization": f"Bearer {token}"}

    got = await client.get(f"/api/v1/locations/{location.id}", headers=headers)
    assert got.status_code == 200
    assert got.json()["businessDayCutoff"].startswith("05:00")

    updated = await client.patch(
        f"/api/v1/locations/{location.id}",
        json={"businessDayCutoff": "04:00"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["businessDayCutoff"].startswith("04:00")
