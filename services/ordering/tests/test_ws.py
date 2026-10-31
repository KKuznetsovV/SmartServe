import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.db.models import Location, User
from app.modules.ordering.ws_router import (
    authorize_socket,
    bind_redis,
    broadcast,
    consume_ws_ticket,
    handle_redis_message,
    issue_ws_ticket,
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
        self.store: dict[str, str] = {}

    async def publish(self, channel: str, message: str) -> None:
        self.published.append((channel, message))

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    async def getdel(self, key: str) -> str | None:
        return self.store.pop(key, None)


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


@pytest.mark.asyncio
async def test_ticket_is_one_time() -> None:
    redis = _FakeRedis()
    bind_redis(redis)
    try:
        ticket = await issue_ws_ticket("loc-1")
        assert await consume_ws_ticket(ticket) == "loc-1"
        assert await consume_ws_ticket(ticket) is None
    finally:
        bind_redis(None)


@pytest.mark.asyncio
async def test_create_ticket_requires_login_and_location(
    client: AsyncClient, owner_user: tuple[User, str], location: Location
) -> None:
    redis = _FakeRedis()
    bind_redis(redis)
    try:
        unauth = await client.post("/api/v1/ws/ticket", json={"locationId": location.id})
        assert unauth.status_code in {401, 403}

        _, token = owner_user
        missing = await client.post(
            "/api/v1/ws/ticket",
            json={"locationId": "00000000-0000-0000-0000-000000000000"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert missing.status_code == 404

        ok = await client.post(
            "/api/v1/ws/ticket",
            json={"locationId": location.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert ok.status_code == 200
        assert ok.json()["ticket"]
        assert ok.json()["expiresIn"] == 60
    finally:
        bind_redis(None)


@pytest.mark.asyncio
async def test_authorize_socket_ticket_and_device(monkeypatch: pytest.MonkeyPatch) -> None:
    redis = _FakeRedis()
    bind_redis(redis)
    try:
        ticket = await issue_ws_ticket("loc-1")
        ws = MagicMock()
        ws.query_params = {"ticket": ticket}
        ws.headers = {}
        assert await authorize_socket(ws, "loc-1")
        assert not await authorize_socket(ws, "loc-1")

        ws_other = MagicMock()
        ws_other.query_params = {"ticket": ticket}
        ws_other.headers = {}
        assert not await authorize_socket(ws_other, "loc-2")

        async def _kds(_raw: str | None) -> dict:
            return {"locationId": "loc-1", "type": "kds"}

        monkeypatch.setattr("app.modules.ordering.ws_router.device_for_token", _kds)
        device_ws = MagicMock()
        device_ws.query_params = {"deviceToken": "secret"}
        device_ws.headers = {}
        assert await authorize_socket(device_ws, "loc-1")

        async def _pos(_raw: str | None) -> dict:
            return {"locationId": "loc-1", "type": "pos"}

        monkeypatch.setattr("app.modules.ordering.ws_router.device_for_token", _pos)
        pos_ws = MagicMock()
        pos_ws.query_params = {"deviceToken": "secret"}
        pos_ws.headers = {}
        assert not await authorize_socket(pos_ws, "loc-1")

        anon = MagicMock()
        anon.query_params = {}
        anon.headers = {}
        assert not await authorize_socket(anon, "loc-1")
    finally:
        bind_redis(None)
