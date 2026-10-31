"""Redis-backed failure counters for PIN and password lockout (HTTP 423)."""

from __future__ import annotations

import math
import time
from typing import Any, NoReturn, Protocol

from fastapi import HTTPException, status

from smartserve_shared.outbox import enqueue

DEFAULT_MAX_FAILURES = 5
DEFAULT_LOCKOUT_SECONDS = 15 * 60
LOCKOUT_DETAIL = "Too many attempts"


class RedisLike(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def incr(self, key: str) -> int: ...
    async def expire(self, key: str, seconds: int) -> bool: ...
    async def set(self, key: str, value: str, ex: int | None = None) -> bool | None: ...
    async def ttl(self, key: str) -> int: ...
    async def delete(self, *keys: str) -> int: ...


def pin_ident(user_id: str, device_id: str | None = None) -> str:
    ident = f"user:{user_id}"
    if device_id:
        return f"{ident}:device:{device_id}"
    return ident


def email_ident(email: str) -> str:
    return f"email:{email.strip().lower()}"


def fail_key(ident: str) -> str:
    return f"lockout:fail:{ident}"


def block_key(ident: str) -> str:
    return f"lockout:block:{ident}"


def locked_http(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_423_LOCKED,
        detail=LOCKOUT_DETAIL,
        headers={"Retry-After": str(max(int(retry_after), 1))},
    )


async def remaining_lockout(redis: RedisLike | None, ident: str) -> int:
    if redis is None:
        return 0
    ttl = await redis.ttl(block_key(ident))
    if ttl is None or ttl < 0:
        return DEFAULT_LOCKOUT_SECONDS if ttl == -1 else 0
    return max(int(ttl), 1)


async def raise_if_locked(redis: RedisLike | None, ident: str) -> None:
    retry_after = await remaining_lockout(redis, ident)
    if retry_after:
        raise locked_http(retry_after)


async def record_failure(
    redis: RedisLike | None,
    ident: str,
    *,
    max_failures: int = DEFAULT_MAX_FAILURES,
    lockout_seconds: int = DEFAULT_LOCKOUT_SECONDS,
) -> int | None:
    """Increment the failure counter. Returns Retry-After seconds when now locked."""
    if redis is None:
        return None
    key = fail_key(ident)
    count = int(await redis.incr(key))
    if count == 1:
        await redis.expire(key, lockout_seconds)
    if count < max_failures:
        return None
    blocked = block_key(ident)
    await redis.set(blocked, "1", ex=lockout_seconds)
    ttl = await redis.ttl(blocked)
    return ttl if ttl and ttl > 0 else lockout_seconds


async def clear_failures(redis: RedisLike | None, ident: str) -> None:
    if redis is None:
        return
    await redis.delete(fail_key(ident), block_key(ident))


async def emit_lockout(
    db: Any,
    outbox_model: type,
    *,
    business_id: str | None,
    user_id: str | None,
    device_id: str | None = None,
) -> None:
    if db is None or outbox_model is None or not user_id:
        return
    await enqueue(
        db,
        outbox_model,
        "auth.lockout",
        {
            "businessId": business_id,
            "userId": user_id,
            "deviceId": device_id,
        },
        business_id=business_id,
    )


async def raise_now_locked(db: Any, retry_after: int) -> NoReturn:
    """Commit outbox rows written in this request, then return 423."""
    if db is not None:
        await db.commit()
    raise locked_http(retry_after)


class InMemoryRedis:
    """Minimal async Redis subset for tests (TTL via monotonic clock)."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._deadline: dict[str, float] = {}

    def _purge(self, key: str) -> None:
        deadline = self._deadline.get(key)
        if deadline is not None and deadline <= time.monotonic():
            self._store.pop(key, None)
            self._deadline.pop(key, None)

    async def get(self, key: str) -> str | None:
        self._purge(key)
        return self._store.get(key)

    async def incr(self, key: str) -> int:
        self._purge(key)
        value = int(self._store.get(key, "0")) + 1
        self._store[key] = str(value)
        return value

    async def expire(self, key: str, seconds: int) -> bool:
        self._purge(key)
        if key not in self._store:
            return False
        self._deadline[key] = time.monotonic() + seconds
        return True

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self._store[key] = value
        if ex is None:
            self._deadline.pop(key, None)
        else:
            self._deadline[key] = time.monotonic() + ex
        return True

    async def ttl(self, key: str) -> int:
        self._purge(key)
        if key not in self._store:
            return -2
        deadline = self._deadline.get(key)
        if deadline is None:
            return -1
        return max(math.ceil(deadline - time.monotonic()), 0)

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self._store or key in self._deadline:
                removed += 1
            self._store.pop(key, None)
            self._deadline.pop(key, None)
        return removed
