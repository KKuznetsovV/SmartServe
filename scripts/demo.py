"""One-command local start: compose up, migrate, seed demo data, print logins."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start SmartServe with demo data.")
    parser.add_argument("--rebuild", action="store_true", help="Pass --build to docker compose up.")
    parser.add_argument("--reset", action="store_true", help="Wipe compose volumes first (fresh database).")
    parser.add_argument(
        "--stack",
        action="store_true",
        help="Apply docker-compose.stack.yml (CI API suite fault injection).",
    )
    args = parser.parse_args()

    (ROOT / "models").mkdir(exist_ok=True)

    compose = ["docker", "compose", "-f", "docker-compose.yml"]
    if args.stack:
        compose += ["-f", "docker-compose.stack.yml"]

    if args.reset:
        _run([*compose, "down", "-v"])

    up = [*compose, "up", "-d", "--wait"]
    if args.rebuild:
        up = [*compose, "up", "-d", "--build", "--wait"]
    _run(up)
    _run(
        [
            *compose,
            "exec",
            "-T",
            "auth",
            "python",
            "-m",
            "app.db.seed",
            "--with-second-tenant",
        ]
    )
    _run([sys.executable, str(ROOT / "scripts" / "seed_demo.py")])

    print()
    print("SmartServe is up.")
    print("  Admin:    http://localhost:3000")
    print("  Orders:   http://localhost:3001")
    print("  Gateway:  http://localhost:8080")
    print()
    print("Demo logins")
    print("  owner    owner@demo.com / demo1234")
    print("  manager  manager@demo.com / demo1234  (PIN 2222)")
    print("  waiter   PIN 1234")
    print("  kitchen  PIN 5678")
    print("  other    owner@other.com / other1234")


if __name__ == "__main__":
    main()
