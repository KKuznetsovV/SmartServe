"""E5b: orders stay writable when RabbitMQ is down; the outbox drains after it returns."""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import asyncpg
import pytest
from httpx import AsyncClient

from conftest import add_item, bearer, create_order, submit_order

REPO_ROOT = Path(__file__).resolve().parents[2]


def _database_url() -> str:
    if url := os.environ.get("SMARTSERVE_API_DATABASE_URL"):
        return url
    user = os.environ.get("POSTGRES_USER", "smartserve")
    password = os.environ.get("POSTGRES_PASSWORD", "smartserve")
    db = os.environ.get("POSTGRES_DB", "smartserve")
    return f"postgresql://{user}:{password}@localhost:5432/{db}"


@pytest.mark.stack
async def test_e5_outbox_survives_broker_outage(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    if os.environ.get("SMARTSERVE_STACK") != "1":
        pytest.skip("stack-only: set SMARTSERVE_STACK=1 in the compose API suite")

    location_id = waiter_a["locationId"]
    token = waiter_a["token"]
    _compose(["stop", "rabbitmq"])
    try:
        order = await create_order(client, token, location_id)
        item = await add_item(client, token, order["id"], catalog["burgerId"], fire_course=2)
        submitted = await submit_order(client, token, order["id"])
        assert submitted["status"] == "submitted"
        fired = await client.post(
            f"/orders/{order['id']}/fire-course",
            headers=bearer(token),
            json={"course": 2},
        )
        assert fired.status_code == 200

        db = await asyncpg.connect(_database_url())
        try:
            unsent = await db.fetchval(
                "SELECT count(*) FROM ordering_outbox WHERE published_at IS NULL AND payload LIKE $1",
                f'%"{order["id"]}"%',
            )
        finally:
            await db.close()
        assert unsent >= 1
    finally:
        _compose(["start", "rabbitmq"])
        await _wait_rabbit()

    db = await asyncpg.connect(DATABASE_URL)
    try:
        reporting_count = 0
        print_jobs = 0
        for _ in range(30):
            reporting_count = await db.fetchval(
                "SELECT count(*) FROM reporting_orders WHERE id = $1",
                order["id"],
            )
            print_jobs = await db.fetchval(
                "SELECT count(*) FROM print_jobs WHERE order_id = $1 AND item_id = $2",
                order["id"],
                item["id"],
            )
            if reporting_count == 1 and print_jobs == 1:
                break
            await asyncio.sleep(1)
        assert reporting_count == 1
        assert print_jobs == 1
    finally:
        await db.close()


def _compose(args: list[str]) -> None:
    subprocess.run(["docker", "compose", *args], cwd=REPO_ROOT, check=True)


async def _wait_rabbit() -> None:
    for _ in range(40):
        ping = subprocess.run(
            ["docker", "compose", "exec", "-T", "rabbitmq", "rabbitmq-diagnostics", "-q", "ping"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        )
        if ping.returncode == 0:
            return
        await asyncio.sleep(1)
    raise RuntimeError("rabbitmq did not become healthy after start")
