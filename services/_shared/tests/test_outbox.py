from __future__ import annotations

import asyncio
import json
import tempfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from smartserve_shared.db import Base
from smartserve_shared.outbox import (
    cleanup_published,
    claim_event,
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


async def test_concurrent_relay_once_publishes_each_row_once() -> None:
    tmp = Path(tempfile.mkdtemp()) / "outbox.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp.as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        for i in range(50):
            await enqueue(session, Outbox, "order.updated", {"orderId": f"o-{i}"})
        await session.commit()

    published: list[str] = []

    async def fake_publish(_conn, routing_key: str, payload: dict) -> bool:
        published.append(payload["orderId"])
        await asyncio.sleep(0)
        return True

    async def run_relay() -> int:
        async with factory() as session:
            with patch("smartserve_shared.mq.publish", new=fake_publish):
                return await relay_once("conn", session, Outbox)

    try:
        sent_a, sent_b = await asyncio.gather(run_relay(), run_relay())
        assert sent_a + sent_b == 50
        assert len(published) == 50
        assert len(set(published)) == 50
    finally:
        await engine.dispose()


async def test_duplicate_event_id_runs_handler_once() -> None:
    calls: list[str] = []

    async def handler(_routing_key: str, payload: dict, _session) -> None:
        calls.append(payload["eventId"])

    async for _unused_session, factory in _open_session():
        await handle_idempotent(factory, Processed, handler, "order.updated", {"eventId": "e1"})
        await handle_idempotent(factory, Processed, handler, "order.updated", {"eventId": "e1"})
        assert calls == ["e1"]
        async with factory() as session:
            assert await session.get(Processed, "e1") is not None


async def test_handler_raise_leaves_no_processed_row() -> None:
    async def handler(_routing_key: str, _payload: dict, _session) -> None:
        raise RuntimeError("boom")

    async for _unused_session, factory in _open_session():
        with pytest.raises(RuntimeError, match="boom"):
            await handle_idempotent(factory, Processed, handler, "order.updated", {"eventId": "e-fail"})
        async with factory() as session:
            assert await session.get(Processed, "e-fail") is None
            assert await claim_event(session, Processed, "e-fail") == "e-fail"


async def test_cleanup_deletes_old_published_rows() -> None:
    async for session, _factory in _open_session():
        old = await enqueue(session, Outbox, "order.created", {"orderId": "old"})
        recent = await enqueue(session, Outbox, "order.created", {"orderId": "new"})
        await session.commit()
        old.published_at = datetime.now(UTC) - timedelta(days=8)
        recent.published_at = datetime.now(UTC)
        await session.commit()
        deleted = await cleanup_published(session, Outbox)
        assert deleted == 1
        left = (await session.execute(select(Outbox))).scalars().all()
        assert [json.loads(row.payload)["orderId"] for row in left] == ["new"]
