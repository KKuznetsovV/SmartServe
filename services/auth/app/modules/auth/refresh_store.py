"""Redis refresh-token families: rotate on use, revoke the family on reuse or logout."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from smartserve_shared.security import decode_token, refresh_expire_seconds

FAM_PREFIX = "refresh:fam:"
JTI_PREFIX = "refresh:jti:"
REVOKED = "revoked"


def _ttl() -> int:
    return refresh_expire_seconds()


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


async def register(redis: Any, *, family_id: str, jti: str) -> None:
    if redis is None:
        return
    ttl = _ttl()
    await redis.set(f"{FAM_PREFIX}{family_id}", jti, ex=ttl)
    await redis.set(f"{JTI_PREFIX}{jti}", family_id, ex=ttl)


async def revoke_family(redis: Any, family_id: str | None) -> None:
    if redis is None or not family_id:
        return
    fam_key = f"{FAM_PREFIX}{family_id}"
    current = _as_str(await redis.get(fam_key))
    await redis.set(fam_key, REVOKED, ex=_ttl())
    if current and current != REVOKED:
        await redis.delete(f"{JTI_PREFIX}{current}")


async def revoke_presented(redis: Any, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except HTTPException:
        return
    await revoke_family(redis, payload.get("fam"))


async def rotate(redis: Any, *, presented_jti: str, family_id: str, new_jti: str) -> None:
    if redis is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    fam_key = f"{FAM_PREFIX}{family_id}"
    current = _as_str(await redis.get(fam_key))
    if current is None or current == REVOKED:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if current != presented_jti:
        await revoke_family(redis, family_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    ttl = _ttl()
    await redis.delete(f"{JTI_PREFIX}{presented_jti}")
    await redis.set(fam_key, new_jti, ex=ttl)
    await redis.set(f"{JTI_PREFIX}{new_jti}", family_id, ex=ttl)
