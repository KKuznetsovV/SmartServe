"""Tests for staff.created/staff.updated publish call sites (mocked mq.publish)."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.db.models import User


@pytest.mark.asyncio
async def test_create_staff_publishes_staff_created(
    client: AsyncClient,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.core.mq.publish", new_callable=AsyncMock) as mock_publish:
        resp = await client.post(
            "/api/v1/staff",
            json={"name": "Waiter Bob", "role": "waiter", "pin": "1234"},
            headers=headers,
        )
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    mock_publish.assert_awaited_once()
    _, routing_key, payload = mock_publish.await_args.args
    assert routing_key == "staff.created"
    assert payload["userId"] == user_id
    assert payload["role"] == "waiter"


@pytest.mark.asyncio
async def test_update_staff_publishes_staff_updated(
    client: AsyncClient,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    created = (
        await client.post(
            "/api/v1/staff",
            json={"name": "Waiter Bob", "role": "waiter", "pin": "1234"},
            headers=headers,
        )
    ).json()

    with patch("app.core.mq.publish", new_callable=AsyncMock) as mock_publish:
        resp = await client.patch(f"/api/v1/staff/{created['id']}", json={"name": "Robert"}, headers=headers)
    assert resp.status_code == 200

    mock_publish.assert_awaited_once()
    _, routing_key, payload = mock_publish.await_args.args
    assert routing_key == "staff.updated"
    assert payload["userId"] == created["id"]
    assert payload["name"] == "Robert"
