"""Transactional outbox: enqueue in the request transaction, relay after commit.

Each publishing service maps `<service>_outbox` via `declare_outbox`. Consumers map
`<service>_processed_events` via `declare_processed_events` and skip duplicate `eventId`s.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

logger = logging.getLogger("smartserve.outbox")

RELAY_POLL_SECONDS = 1.0
RELAY_BATCH_SIZE = 50


def declare_outbox(base: type, table_name: str) -> type:
    """Mapped outbox row class bound to `base` for `table_name`."""

    class OutboxRow(base):
        __tablename__ = table_name
        __table_args__ = (
            UniqueConstraint("event_id", name=f"uq_{table_name}_event_id"),
            Index(f"ix_{table_name}_unpublished", "published_at", "occurred_at"),
        )

        id: Mapped[str] = mapped_column(String(), primary_key=True, default=lambda: str(uuid.uuid4()))
        routing_key: Mapped[str] = mapped_column(String(255), nullable=False)
        payload: Mapped[str] = mapped_column(Text, nullable=False)
        event_id: Mapped[str] = mapped_column(String(), nullable=False)
        business_id: Mapped[str | None] = mapped_column(String(), nullable=True)
        occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
        published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
        last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    OutboxRow.__name__ = "".join(part.title() for part in table_name.split("_"))
    OutboxRow.__qualname__ = OutboxRow.__name__
    return OutboxRow


def declare_processed_events(base: type, table_name: str) -> type:
    """Mapped processed-event id class bound to `base` for `table_name`."""

    class ProcessedEvent(base):
        __tablename__ = table_name

        event_id: Mapped[str] = mapped_column(String(), primary_key=True)
        processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    ProcessedEvent.__name__ = "".join(part.title() for part in table_name.split("_"))
    ProcessedEvent.__qualname__ = ProcessedEvent.__name__
    return ProcessedEvent


def create_outbox_table(op: Any, table_name: str) -> None:
    import sqlalchemy as sa

    op.create_table(
        table_name,
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("routing_key", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("business_id", sa.String(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.UniqueConstraint("event_id", name=f"uq_{table_name}_event_id"),
    )
    op.create_index(f"ix_{table_name}_unpublished", table_name, ["published_at", "occurred_at"])


def create_processed_events_table(op: Any, table_name: str) -> None:
    import sqlalchemy as sa

    op.create_table(
        table_name,
        sa.Column("event_id", sa.String(), primary_key=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
    )


def drop_outbox_table(op: Any, table_name: str) -> None:
    op.drop_index(f"ix_{table_name}_unpublished", table_name=table_name)
    op.drop_table(table_name)


def drop_processed_events_table(op: Any, table_name: str) -> None:
    op.drop_table(table_name)


async def enqueue(
    db: Any,
    model: type,
    routing_key: str,
    payload: dict[str, Any],
    *,
    business_id: str | None = None,
) -> Any:
    """Insert an outbox row in the caller's transaction. Never talks to the broker."""
    body = dict(payload)
    event_id = body.get("eventId") or str(uuid.uuid4())
    body["eventId"] = event_id
    if not body.get("occurredAt"):
        body["occurredAt"] = datetime.now(UTC).isoformat()
    if business_id and not body.get("businessId"):
        body["businessId"] = business_id
    biz = body.get("businessId") if isinstance(body.get("businessId"), str) else business_id
    occurred_raw = body["occurredAt"]
    try:
        occurred_at = datetime.fromisoformat(str(occurred_raw).replace("Z", "+00:00"))
    except ValueError:
        occurred_at = datetime.now(UTC)
        body["occurredAt"] = occurred_at.isoformat()
    row = model(
        routing_key=routing_key,
        payload=json.dumps(body),
        event_id=event_id,
        business_id=biz,
        occurred_at=occurred_at,
        attempts=0,
    )
    db.add(row)
    await db.flush()
    return row


async def relay_once(connection: Any, session: Any, model: type, *, batch_size: int = RELAY_BATCH_SIZE) -> int:
    """Publish a batch of unpublished rows. Marks a row sent only if publish succeeds."""
    result = await session.execute(
        select(model).where(model.published_at.is_(None)).order_by(model.occurred_at.asc()).limit(batch_size)
    )
    rows = list(result.scalars().all())
    sent = 0
    now = datetime.now(UTC)
    from smartserve_shared import mq

    for row in rows:
        row.attempts = int(row.attempts or 0) + 1
        try:
            payload = json.loads(row.payload)
        except json.JSONDecodeError:
            row.last_error = "unparsable payload"
            continue
        ok = await mq.publish(connection, row.routing_key, payload)
        if ok:
            row.published_at = now
            row.last_error = None
            sent += 1
        else:
            row.last_error = "publish failed"
    await session.commit()
    return sent


async def relay_forever(
    get_connection: Callable[[], Any],
    session_factory: Callable[[], Any],
    model: type,
    *,
    poll_seconds: float = RELAY_POLL_SECONDS,
) -> None:
    """Background loop: publish unpublished outbox rows, reconnecting via `get_connection`."""
    while True:
        try:
            connection = get_connection()
            async with session_factory() as session:
                await relay_once(connection, session, model)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — keep the relay alive across poll failures
            logger.warning("outbox.relay: poll failed, retrying", exc_info=True)
        await asyncio.sleep(poll_seconds)


async def already_processed(session_factory: Callable[[], Any], model: type, event_id: str) -> bool:
    async with session_factory() as session:
        row = await session.get(model, event_id)
        return row is not None


async def record_processed(session_factory: Callable[[], Any], model: type, event_id: str) -> None:
    async with session_factory() as session:
        if await session.get(model, event_id) is not None:
            return
        session.add(model(event_id=event_id, processed_at=datetime.now(UTC)))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()


async def handle_idempotent(
    session_factory: Callable[[], Any] | None,
    processed_model: type | None,
    handler: Callable[..., Any],
    routing_key: str,
    payload: dict[str, Any],
) -> None:
    event_id = payload.get("eventId")
    if event_id and session_factory is not None and processed_model is not None:
        if await already_processed(session_factory, processed_model, str(event_id)):
            return
        await handler(routing_key, payload)
        await record_processed(session_factory, processed_model, str(event_id))
        return
    await handler(routing_key, payload)
