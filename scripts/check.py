"""Cross-platform check runner for SmartServe services and frontends.

Usage:
  python scripts/check.py --services auth,catalog
  python scripts/check.py --frontend web,orders
  python scripts/check.py --api
  python scripts/check.py --changed
  python scripts/check.py --all
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVICES = (
    "auth",
    "catalog",
    "ordering",
    "payments",
    "staff",
    "printing",
    "reporting",
    "ai",
)
FRONTENDS = ("web", "orders")
PNPM_PACKAGES = {
    "web": "@smartserve/web",
    "orders": "@smartserve/orders",
}


@dataclass
class CheckResult:
    target: str
    check: str
    ok: bool
    detail: str = ""


def venv_python(service: str) -> Path:
    base = REPO_ROOT / "services" / service / ".venv"
    windows = base / "Scripts" / "python.exe"
    if windows.exists():
        return windows
    return base / "bin" / "python"


def run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )


def fail_detail(proc: subprocess.CompletedProcess[str]) -> str:
    text = (proc.stdout or "") + (proc.stderr or "")
    lines = [line for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return f"exit {proc.returncode}"
    return lines[-1][:200]


def targets_from_changed(files: list[str]) -> tuple[set[str], set[str], bool]:
    """Map changed paths (relative to repo root) to services, frontends, and the API suite."""
    services: set[str] = set()
    frontends: set[str] = set()
    api = False
    all_services = False
    for raw in files:
        path = raw.replace("\\", "/")
        if path.startswith("services/_shared/") or path.startswith("services/gateway/"):
            all_services = True
        for name in SERVICES:
            if path.startswith(f"services/{name}/"):
                services.add(name)
        for name in FRONTENDS:
            if path.startswith(f"apps/{name}/"):
                frontends.add(name)
        if path.startswith("packages/"):
            frontends.update(FRONTENDS)
        if path.startswith("tests/api/"):
            api = True
    if all_services:
        services = set(SERVICES)
    return services, frontends, api


def changed_files_vs_main() -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", "main...HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git diff failed")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def check_service(name: str) -> list[CheckResult]:
    python = venv_python(name)
    cwd = REPO_ROOT / "services" / name
    results: list[CheckResult] = []
    if not python.exists():
        return [
            CheckResult(
                name,
                "venv",
                False,
                f"missing {python.relative_to(REPO_ROOT)}; create it with python -m venv .venv",
            )
        ]

    env = os.environ.copy()
    extra_path = [REPO_ROOT / "services" / "_shared" / "src"]
    env["PYTHONPATH"] = os.pathsep.join(
        [str(p) for p in extra_path] + [env[k] for k in ("PYTHONPATH",) if k in env]
    )

    checks = [
        ("ruff check", [str(python), "-m", "ruff", "check", "app/"]),
        ("ruff format", [str(python), "-m", "ruff", "format", "--check", "app/"]),
        (
            "mypy",
            [
                str(python),
                "-m",
                "mypy",
                "app/",
                "--ignore-missing-imports",
                "--explicit-package-bases",
            ],
        ),
        ("pytest", [str(python), "-m", "pytest", "-q"]),
    ]
    for label, cmd in checks:
        proc = run(cmd, cwd=cwd, env=env)
        results.append(CheckResult(name, label, proc.returncode == 0, fail_detail(proc) if proc.returncode else ""))
    return results


def build_shared_packages() -> list[CheckResult]:
    results: list[CheckResult] = []
    for pkg in ("@smartserve/types", "@smartserve/api-client"):
        proc = run(["pnpm", "--filter", pkg, "build"], cwd=REPO_ROOT)
        results.append(
            CheckResult(
                pkg,
                "tsup build",
                proc.returncode == 0,
                fail_detail(proc) if proc.returncode else "",
            )
        )
    return results


def check_frontend(name: str) -> list[CheckResult]:
    cwd = REPO_ROOT / "apps" / name
    pkg = PNPM_PACKAGES[name]
    results: list[CheckResult] = []
    for label, script in (
        ("typecheck", "typecheck"),
        ("lint", "lint"),
        ("vitest", "test"),
        ("next build", "build"),
    ):
        proc = run(["pnpm", "--filter", pkg, script], cwd=REPO_ROOT)
        results.append(CheckResult(name, label, proc.returncode == 0, fail_detail(proc) if proc.returncode else ""))
    return results


def check_api() -> CheckResult:
    api_dir = REPO_ROOT / "tests" / "api"
    if not api_dir.exists():
        return CheckResult("api", "pytest", True, "tests/api not present yet; skipped")
    proc = run([sys.executable, "-m", "pytest", "tests/api", "-q"], cwd=REPO_ROOT)
    return CheckResult("api", "pytest", proc.returncode == 0, fail_detail(proc) if proc.returncode else "")


def print_summary(results: list[CheckResult]) -> None:
    if not results:
        print("Nothing to check.")
        return
    width_t = max(len(r.target) for r in results)
    width_c = max(len(r.check) for r in results)
    print()
    print(f"{'target'.ljust(width_t)}  {'check'.ljust(width_c)}  result")
    print(f"{'-' * width_t}  {'-' * width_c}  ------")
    for r in results:
        status = "ok" if r.ok else "FAIL"
        line = f"{r.target.ljust(width_t)}  {r.check.ljust(width_c)}  {status}"
        if not r.ok and r.detail:
            line += f"  {r.detail}"
        print(line)


def parse_csv(value: str | None, allowed: tuple[str, ...], flag: str) -> list[str]:
    if not value:
        return []
    names = [part.strip() for part in value.split(",") if part.strip()]
    unknown = [name for name in names if name not in allowed]
    if unknown:
        raise SystemExit(f"unknown {flag} value(s): {', '.join(unknown)}")
    return names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SmartServe lint, typecheck and tests.")
    parser.add_argument("--services", help="Comma-separated service names")
    parser.add_argument("--frontend", help="Comma-separated frontend apps (web, orders)")
    parser.add_argument("--api", action="store_true", help="Run tests/api against a running stack")
    parser.add_argument("--changed", action="store_true", help="Infer targets from git diff main...HEAD")
    parser.add_argument("--all", action="store_true", help="Run every service, both apps, and tests/api")
    args = parser.parse_args(argv)

    if not any((args.services, args.frontend, args.api, args.changed, args.all)):
        parser.print_help()
        return 2

    services: set[str] = set()
    frontends: set[str] = set()
    api = False

    if args.all:
        services = set(SERVICES)
        frontends = set(FRONTENDS)
        api = True
    if args.changed:
        files = changed_files_vs_main()
        s, f, a = targets_from_changed(files)
        services.update(s)
        frontends.update(f)
        api = api or a
        if not files:
            print("No files changed vs main.")
    services.update(parse_csv(args.services, SERVICES, "--services"))
    frontends.update(parse_csv(args.frontend, FRONTENDS, "--frontend"))
    api = api or args.api

    results: list[CheckResult] = []
    for name in SERVICES:
        if name in services:
            results.extend(check_service(name))
    if frontends:
        results.extend(build_shared_packages())
        for name in FRONTENDS:
            if name in frontends:
                results.extend(check_frontend(name))
    if api:
        results.append(check_api())

    print_summary(results)
    failed = [r for r in results if not r.ok]
    if failed:
        print(f"\n{len(failed)} check(s) failed.")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
