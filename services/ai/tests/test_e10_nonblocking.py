import asyncio
import time

import httpx

from app.clients import auth_client
from app.core.config import settings


async def test_slow_classifier_does_not_block_health(client, manager_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")

    def slow_classify(_message):
        time.sleep(2)
        return None

    monkeypatch.setattr("app.modules.ai.router.local_classify", slow_classify)

    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "loc-1", "businessId": "biz-1", "timezone": "UTC"})

    monkeypatch.setattr(auth_client, "get", fake_auth_get)

    command_task = asyncio.create_task(
        client.post(
            "/api/v1/ai/command",
            json={"message": "add a pizza", "context": {"locationId": "loc-1"}},
            headers={"Authorization": f"Bearer {manager_token}"},
        )
    )
    started = time.perf_counter()
    await asyncio.sleep(0.05)
    health = await client.get("/api/v1/health")
    elapsed = time.perf_counter() - started
    assert health.status_code == 200
    assert elapsed < 0.2

    command = await command_task
    assert command.status_code == 503
