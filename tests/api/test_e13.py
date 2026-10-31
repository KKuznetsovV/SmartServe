"""E13: every OpenAPI prefix is reachable through the gateway with X-Served-By."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")
SERVICES = ("auth", "catalog", "ordering", "payments", "staff", "printing", "reporting", "ai")
SKIP_PATHS = {"/api/v1/health", "/api/v1/ready"}
PLACEHOLDER = "00000000-0000-0000-0000-000000000001"


def _compose_exec(service: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", "exec", "-T", service, *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )


def _openapi(service: str) -> dict:
    code = (
        "import urllib.request,sys;"
        "sys.stdout.write(urllib.request.urlopen('http://127.0.0.1:8000/openapi.json').read().decode())"
    )
    proc = _compose_exec(service, "python", "-c", code)
    return json.loads(proc.stdout)


def _route_prefix(path: str) -> str:
    parts = [p for p in path.split("/") if p]
    if len(parts) < 3:
        return path
    rest = parts[2:]
    first = rest[0]
    if len(rest) >= 3 and rest[1].startswith("{") and not rest[2].startswith("{"):
        return f"/api/v1/{first}/{{id}}/{rest[2]}"
    return f"/api/v1/{first}"


def _sample_paths(spec: dict) -> dict[str, tuple[str, str]]:
    samples: dict[str, tuple[str, str]] = {}
    for path, ops in (spec.get("paths") or {}).items():
        if path in SKIP_PATHS:
            continue
        if path.startswith("/api/v1/ws/") and path != "/api/v1/ws/ticket":
            continue
        methods = [m for m in ("get", "post", "put", "patch", "delete") if m in ops]
        if not methods:
            continue
        prefix = _route_prefix(path)
        samples.setdefault(prefix, (path, methods[0]))
    return samples


@pytest.mark.stack
async def test_e13_gateway_serves_one_path_per_openapi_prefix() -> None:
    if os.environ.get("SMARTSERVE_STACK") != "1":
        pytest.skip("stack-only: set SMARTSERVE_STACK=1 in the compose API suite")

    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=30.0) as gateway:
        for service in SERVICES:
            spec = _openapi(service)
            samples = _sample_paths(spec)
            assert samples, f"{service} published no routable OpenAPI paths"
            for prefix, (path, method) in sorted(samples.items()):
                concrete = re.sub(r"\{[^}]+\}", PLACEHOLDER, path)
                resp = await gateway.request(method, concrete)
                served = resp.headers.get("X-Served-By")
                assert served == service, (
                    f"{service} prefix {prefix} path {method.upper()} {concrete} "
                    f"status={resp.status_code} served-by={served!r} body={resp.text[:200]!r}"
                )
