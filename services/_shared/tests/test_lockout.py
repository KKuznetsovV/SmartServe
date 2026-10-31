import asyncio

import pytest
from fastapi import HTTPException

from smartserve_shared.lockout import (
    InMemoryRedis,
    clear_failures,
    email_ident,
    pin_ident,
    raise_if_locked,
    record_failure,
    remaining_lockout,
)


@pytest.mark.asyncio
async def test_five_failures_lock_even_when_the_secret_is_correct() -> None:
    redis = InMemoryRedis()
    ident = pin_ident("user-1", "device-1")
    for _ in range(4):
        assert (
            await record_failure(redis, ident, max_failures=5, lockout_seconds=60)
            is None
        )
        await raise_if_locked(redis, ident)

    retry = await record_failure(redis, ident, max_failures=5, lockout_seconds=60)
    assert retry is not None
    assert retry > 0
    with pytest.raises(HTTPException) as locked:
        await raise_if_locked(redis, ident)
    assert locked.value.status_code == 423
    assert locked.value.headers["Retry-After"] == str(retry)


@pytest.mark.asyncio
async def test_successful_attempt_resets_the_counter() -> None:
    redis = InMemoryRedis()
    ident = email_ident("Owner@Demo.com")
    for _ in range(4):
        await record_failure(redis, ident, max_failures=5, lockout_seconds=60)
    await clear_failures(redis, ident)
    assert await remaining_lockout(redis, ident) == 0
    assert (
        await record_failure(redis, ident, max_failures=5, lockout_seconds=60) is None
    )


@pytest.mark.asyncio
async def test_lockout_expires() -> None:
    redis = InMemoryRedis()
    ident = pin_ident("user-2")
    await record_failure(redis, ident, max_failures=1, lockout_seconds=1)
    with pytest.raises(HTTPException):
        await raise_if_locked(redis, ident)
    await asyncio.sleep(1.1)
    await raise_if_locked(redis, ident)


@pytest.mark.asyncio
async def test_missing_redis_is_a_no_op() -> None:
    await raise_if_locked(None, "user:x")
    assert await record_failure(None, "user:x") is None
    await clear_failures(None, "user:x")
