"""GET /events is scoped to the caller's business and never returns unscoped rows."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventLog, User


async def _other_manager(db: AsyncSession) -> tuple[User, str]:
    user = User(
        business_id="biz-other",
        email="other-manager@test.com",
        name="Other Manager",
        role="manager",
        password_hash=hash_password("password123"),
    )
    db.add(user)
    await db.flush()
    token = create_access_token(user.id, {"business_id": user.business_id, "role": user.role})
    return user, token


async def _log(
    db: AsyncSession,
    *,
    routing_key: str,
    payload: str,
    business_id: str | None,
    received_at: datetime | None = None,
) -> EventLog:
    row = EventLog(routing_key=routing_key, payload=payload, business_id=business_id)
    if received_at is not None:
        row.received_at = received_at
    db.add(row)
    await db.flush()
    return row


@pytest.mark.asyncio
async def test_list_events_hides_other_business_and_null_rows(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    a, a_token = manager_user
    _, b_token = await _other_manager(db)
    await _log(db, routing_key="order.created", payload='{"orderId":"a-order"}', business_id=a.business_id)
    await _log(
        db,
        routing_key="payment.completed",
        payload='{"orderId":"a-order","amount":12}',
        business_id=a.business_id,
    )
    await _log(
        db,
        routing_key="ai.action_executed",
        payload='{"intent":"menu.create_item","originalMessage":"add pizza"}',
        business_id=a.business_id,
    )
    await _log(db, routing_key="payment.completed", payload='{"orderId":"b-order"}', business_id="biz-other")
    await _log(db, routing_key="order.created", payload='{"orderId":"orphan"}', business_id=None)

    a_resp = await client.get("/api/v1/events", headers={"Authorization": f"Bearer {a_token}"})
    assert a_resp.status_code == 200
    a_keys = {row["routingKey"] for row in a_resp.json()}
    a_payloads = " ".join(row["payload"] for row in a_resp.json())
    assert "payment.completed" in a_keys
    assert "ai.action_executed" in a_keys
    assert "a-order" in a_payloads
    assert "add pizza" in a_payloads
    assert "b-order" not in a_payloads
    assert "orphan" not in a_payloads

    b_resp = await client.get("/api/v1/events", headers={"Authorization": f"Bearer {b_token}"})
    assert b_resp.status_code == 200
    b_payloads = " ".join(row["payload"] for row in b_resp.json())
    assert "a-order" not in b_payloads
    assert "add pizza" not in b_payloads
    assert "orphan" not in b_payloads
    assert "b-order" in b_payloads

    b_ai = await client.get(
        "/api/v1/events",
        params={"routing_key": "ai.action_executed"},
        headers={"Authorization": f"Bearer {b_token}"},
    )
    assert b_ai.status_code == 200
    assert b_ai.json() == []

    b_pay = await client.get(
        "/api/v1/events",
        params={"routing_key": "payment.completed"},
        headers={"Authorization": f"Bearer {b_token}"},
    )
    assert b_pay.status_code == 200
    assert all("a-order" not in row["payload"] for row in b_pay.json())


@pytest.mark.asyncio
async def test_list_events_since_and_limit(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    user, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    old = datetime.now(UTC) - timedelta(hours=2)
    recent = datetime.now(UTC) - timedelta(minutes=1)
    await _log(db, routing_key="order.created", payload='{"n":1}', business_id=user.business_id, received_at=old)
    await _log(db, routing_key="order.updated", payload='{"n":2}', business_id=user.business_id, received_at=recent)

    since = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
    resp = await client.get("/api/v1/events", params={"since": since}, headers=headers)
    assert resp.status_code == 200
    payloads = [row["payload"] for row in resp.json()]
    assert '{"n":2}' in payloads
    assert '{"n":1}' not in payloads

    limited = await client.get("/api/v1/events", params={"limit": 1}, headers=headers)
    assert limited.status_code == 200
    assert len(limited.json()) == 1
