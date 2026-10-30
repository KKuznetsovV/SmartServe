import json
from unittest.mock import AsyncMock

import pytest

from app.modules.ordering.ws_router import (
    bind_redis,
    broadcast,
    handle_redis_message,
    location_id_from_channel,
    publish_ws,
    register,
    unregister,
)


class _FakeSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.closed = False

    async def send_json(self, event: dict) -> None:
        if self.closed:
            raise RuntimeError("closed")
        self.sent.append(event)


class _FakeRedis:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    async def publish(self, channel: str, message: str) -> None:
        self.published.append((channel, message))


def test_unregister_is_idempotent() -> None:
    ws = _FakeSocket()
    register("loc-1", ws)  # type: ignore[arg-type]
    unregister("loc-1", ws)  # type: ignore[arg-type]
    unregister("loc-1", ws)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_broadcast_skips_already_gone_sockets() -> None:
    live = _FakeSocket()
    dead = _FakeSocket()
    dead.closed = True
    register("loc-1", live)  # type: ignore[arg-type]
    register("loc-1", dead)  # type: ignore[arg-type]
    await broadcast("loc-1", {"type": "order.updated", "locationId": "loc-1"})
    assert live.sent == [{"type": "order.updated", "locationId": "loc-1"}]
    unregister("loc-1", live)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_publish_ws_goes_to_redis_channel() -> None:
    redis = _FakeRedis()
    bind_redis(redis)
    try:
        await publish_ws("loc-1", {"type": "order.created", "locationId": "loc-1", "payload": {"orderId": "o-1"}})
        assert redis.published[0][0] == "ws:loc-1"
        body = json.loads(redis.published[0][1])
        assert body["type"] == "order.created"
        assert body["payload"]["orderId"] == "o-1"
    finally:
        bind_redis(None)


@pytest.mark.asyncio
async def test_redis_message_fans_out_to_local_sockets() -> None:
    first = _FakeSocket()
    second = _FakeSocket()
    register("loc-a", first)  # type: ignore[arg-type]
    register("loc-a", second)  # type: ignore[arg-type]
    event = {"type": "order.updated", "locationId": "loc-a", "payload": {"orderId": "o-1", "id": "o-1"}}
    await handle_redis_message(
        {"type": "pmessage", "pattern": "ws:*", "channel": "ws:loc-a", "data": json.dumps(event)}
    )
    assert first.sent == [event]
    assert second.sent == [event]
    unregister("loc-a", first)  # type: ignore[arg-type]
    unregister("loc-a", second)  # type: ignore[arg-type]


def test_location_id_from_channel() -> None:
    assert location_id_from_channel("ws:abc") == "abc"
    assert location_id_from_channel(b"ws:abc") == "abc"
    assert location_id_from_channel("other") is None


@pytest.mark.asyncio
async def test_publish_ws_falls_back_to_local_when_redis_unbound() -> None:
    ws = _FakeSocket()
    register("loc-1", ws)  # type: ignore[arg-type]
    bind_redis(None)
    await publish_ws("loc-1", {"type": "order.updated"})
    assert ws.sent == [{"type": "order.updated"}]
    unregister("loc-1", ws)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_handle_realtime_uses_publish_ws(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.modules.ordering.events import handle_realtime

    mock = AsyncMock()
    monkeypatch.setattr("app.modules.ordering.events.publish_ws", mock)
    await handle_realtime(
        "order.updated",
        {"orderId": "o-1", "locationId": "loc-1", "status": "submitted", "total": 10, "createdBy": "u"},
        None,  # type: ignore[arg-type]
    )
    _location, event = mock.await_args.args
    assert event["payload"] == {"orderId": "o-1", "id": "o-1", "locationId": "loc-1", "status": "submitted"}
