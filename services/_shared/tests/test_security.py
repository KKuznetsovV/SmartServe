from __future__ import annotations

import pytest
from fastapi import HTTPException

from smartserve_shared.security import (
    TokenError,
    configure_security,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    verify_token,
)


@pytest.fixture(autouse=True)
def _bind_secret() -> None:
    configure_security(secret_key="test-secret-key-for-shared-package")


def test_hash_and_verify_password() -> None:
    hashed = hash_password("s3cret")
    assert hashed != "s3cret"
    assert verify_password("s3cret", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip_checks_type() -> None:
    token = create_access_token("user-1", {"business_id": "b1", "role": "owner"})
    payload = decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["type"] == "access"
    assert payload["business_id"] == "b1"
    with pytest.raises(HTTPException) as exc:
        decode_token(token, expected_type="refresh")
    assert exc.value.status_code == 401


def test_refresh_token_rejected_as_access() -> None:
    token = create_refresh_token("user-1")
    with pytest.raises(HTTPException):
        decode_token(token, expected_type="access")
    payload = decode_token(token, expected_type="refresh")
    assert payload["sub"] == "user-1"


def test_verify_token_returns_claims() -> None:
    token = create_access_token("user-1", {"business_id": "b1", "role": "waiter", "location_id": "loc-1"})
    claims = verify_token(token)
    assert claims.sub == "user-1"
    assert claims.business_id == "b1"
    assert claims.role == "waiter"
    assert claims.location_id == "loc-1"


def test_verify_token_bad_signature() -> None:
    token = create_access_token("user-1")
    configure_security(secret_key="other-secret")
    with pytest.raises(TokenError):
        verify_token(token)


def test_decode_token_garbage() -> None:
    with pytest.raises(HTTPException) as exc:
        decode_token("not-a-jwt")
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid or expired token"
