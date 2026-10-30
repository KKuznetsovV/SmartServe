from __future__ import annotations

import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

from smartserve_shared.db import Base
from smartserve_shared.outbox import (
    already_processed,
    declare_outbox,
    declare_processed_events,
    enqueue,
    handle_idempotent,
    relay_once,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

Outbox = declare_outbox(Base, "test_outbox")
Processed = declare_processed_events(Base, "test_processed_events")


async def _open_session() -> AsyncIterator[tuple[AsyncSession, async_sessionmaker]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session, factory
    finally:
        await engine.dispose()


async def test_enqueue_adds_event_id_occurred_at_business_id() -> None:
    async for session, _factory in _open_session():
        row = await enqueue(
            session,
            Outbox,
            "order.created",
            {"orderId": "o1"},
            business_id="biz-1",
        )
        await session.commit()
        body = json.loads(row.payload)
        assert row.routing_key == "order.created"
        assert row.business_id == "biz-1"
        assert body["eventId"] == row.event_id
        assert body["occurredAt"]
        assert body["businessId"] == "biz-1"
        assert body["orderId"] == "o1"


async def test_relay_leaves_row_unpublished_when_publish_fails() -> None:
    async for session, _factory in _open_session():
        await enqueue(session, Outbox, "order.updated", {"orderId": "o1"}, business_id="b")
        await session.commit()
        with patch("smartserve_shared.mq.publish", new_callable=AsyncMock, return_value=False):
            sent = await relay_once(object(), session, Outbox)
        assert sent == 0
        row = (await session.execute(select(Outbox))).scalar_one()
        assert row.published_at is None
        assert row.attempts == 1
        assert row.last_error == "publish failed"


async def test_relay_marks_published_on_success() -> None:
    async for session, _factory in _open_session():
        await enqueue(session, Outbox, "payment.completed", {"orderId": "o1"})
        await session.commit()
        with patch("smartserve_shared.mq.publish", new_callable=AsyncMock, return_value=True) as mock_publish:
            sent = await relay_once("conn", session, Outbox)
        assert sent == 1
        mock_publish.assert_awaited_once()
        row = (await session.execute(select(Outbox))).scalar_one()
        assert row.published_at is not None
        assert row.last_error is None
        _, routing_key, payload = mock_publish.await_args.args
        assert routing_key == "payment.completed"
        assert payload["orderId"] == "o1"
        assert payload["eventId"]


async def test_handle_idempotent_skips_duplicate_event_id() -> None:
    calls: list[str] = []

    async def handler(_routing_key: str, payload: dict) -> None:
        calls.append(payload["eventId"])

    async for _unused_session, factory in _open_session():
        await handle_idempotent(factory, Processed, handler, "order.updated", {"eventId": "e1"})
        await handle_idempotent(factory, Processed, handler, "order.updated", {"eventId": "e1"})
        assert calls == ["e1"]
        assert await already_processed(factory, Processed, "e1")
