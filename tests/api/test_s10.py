import httpx
import pytest

from conftest import WEB_BASE_URL


@pytest.mark.xfail(strict=True, reason="S10")
async def test_s10_unknown_locale_cookie_renders() -> None:
    try:
        async with httpx.AsyncClient(base_url=WEB_BASE_URL, timeout=30.0) as web:
            resp = await web.get("/login", headers={"Cookie": "locale=fr"})
    except httpx.ConnectError:
        pytest.skip(f"web app not running at {WEB_BASE_URL}")
    assert resp.status_code == 200
