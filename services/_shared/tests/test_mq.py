from __future__ import annotations

from types import SimpleNamespace

from smartserve_shared import mq


async def test_publish_with_no_connection_returns_false() -> None:
    assert await mq.publish(None, "order.updated", {"id": "1"}) is False


async def test_connect_unreachable_returns_none() -> None:
    conn = await mq.connect("amqp://invalid-host:5672/")
    assert conn is None


def test_death_count_sums_x_death() -> None:
    assert mq.death_count(None) == 0
    assert mq.death_count({}) == 0
    assert mq.death_count({"x-death": [{"count": 2}, {"count": 3}]}) == 5
    assert mq.death_count({"x-death": [{"count": mq.MAX_RETRIES}]}) == mq.MAX_RETRIES


def test_management_origin_uses_broker_host() -> None:
    origin, user, password = mq.management_origin("amqp://smartserve:secret@rabbitmq:5672/")
    assert origin == "http://rabbitmq:15672"
    assert user == "smartserve"
    assert password == "secret"


async def test_declare_compatible_queue_omits_dlx_arguments() -> None:
    calls: list[dict] = []

    class Channel:
        async def declare_queue(self, name: str, durable: bool = True, arguments=None, passive: bool = False):
            calls.append({"name": name, "arguments": arguments, "passive": passive, "durable": durable})
            return name

    await mq.declare_compatible_queue(Channel(), "ordering.payment_completed")
    assert calls == [
        {"name": "ordering.payment_completed", "arguments": None, "passive": False, "durable": True}
    ]


async def test_declare_compatible_queue_reuses_existing_on_precondition() -> None:
    class Channel:
        def __init__(self) -> None:
            self.calls = 0

        async def declare_queue(self, name: str, durable: bool = True, arguments=None, passive: bool = False):
            self.calls += 1
            if not passive:
                raise RuntimeError("PRECONDITION_FAILED - inequivalent arg 'x-dead-letter-exchange'")
            return f"passive:{name}"

    channel = Channel()
    queue = await mq.declare_compatible_queue(channel, "ordering.realtime")
    assert queue == "passive:ordering.realtime"
    assert channel.calls == 2


def test_consumers_unhealthy_when_retrying() -> None:
    app = SimpleNamespace(state=SimpleNamespace())
    health = mq.ConsumerHealth()
    mq.register_consumer(app, health)
    assert mq.consumers_unhealthy(app) is True
    health.connected = True
    assert mq.consumers_unhealthy(app) is False
