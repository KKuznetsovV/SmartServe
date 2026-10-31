"""httpOnly refresh cookie scoped to /api/v1/auth."""

from fastapi import Response

from app.core.config import settings

COOKIE_NAME = "refresh_token"
COOKIE_PATH = "/api/v1/auth"


def _secure() -> bool:
    return settings.ENVIRONMENT not in {"development", "test"}


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_secure(),
        samesite="strict",
        path=COOKIE_PATH,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path=COOKIE_PATH, samesite="strict")
