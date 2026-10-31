"""Per-business daily Anthropic call budget, keyed in the location's time zone."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from app.core.config import settings

KEY_PREFIX = "ai:budget:"
DEFAULT_TZ = "Asia/Jerusalem"


def _now_in_zone(tz_name: str | None) -> datetime:
    name = tz_name or DEFAULT_TZ
    if name.upper() in {"UTC", "GMT"}:
        return datetime.now(UTC)
    try:
        return datetime.now(ZoneInfo(name))
    except Exception:
        return datetime.now(UTC)


def budget_day(tz_name: str | None) -> str:
    return _now_in_zone(tz_name).date().isoformat()


def budget_key(business_id: str, tz_name: str | None) -> str:
    return f"{KEY_PREFIX}{business_id}:{budget_day(tz_name)}"


def _ttl_seconds(tz_name: str | None) -> int:
    now = _now_in_zone(tz_name)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(int((tomorrow - now).total_seconds()) + 3600, 3600)


async def ensure_budget(redis: Any, business_id: str | None, tz_name: str | None) -> None:
    if redis is None or not business_id:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI call budget exceeded for this business",
        )
    raw = await redis.get(budget_key(business_id, tz_name))
    used = int(raw or 0)
    if used >= settings.AI_DAILY_CALL_BUDGET:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI call budget exceeded for this business",
        )


async def record_call(redis: Any, business_id: str | None, tz_name: str | None) -> None:
    if redis is None or not business_id:
        return
    key = budget_key(business_id, tz_name)
    used = await redis.incr(key)
    if used == 1:
        await redis.expire(key, _ttl_seconds(tz_name))


async def billed_create_message(redis: Any, business_id: str | None, tz_name: str | None, client, **kwargs):
    from app.modules.ai.services.client import create_message

    await ensure_budget(redis, business_id, tz_name)
    try:
        return await create_message(client, **kwargs)
    finally:
        await record_call(redis, business_id, tz_name)
