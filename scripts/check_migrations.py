"""Upgrade every Alembic chain on an empty database, then report drift.

Usage:
  DATABASE_URL=postgresql+asyncpg://... python scripts/check_migrations.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHARED_SRC = REPO_ROOT / "services" / "_shared" / "src"
# Foreign keys cross services, so this order is required on a blank database.
ALEMBIC_SERVICES = (
    "auth",
    "catalog",
    "ordering",
    "payments",
    "staff",
    "printing",
    "reporting",
    "ai",
)


def run(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    print("+", " ".join(cmd), f"(cwd={cwd.name})", flush=True)
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> int:
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://smartserve:smartserve@localhost:5432/smartserve",
    )
    python = sys.executable
    for name in ALEMBIC_SERVICES:
        cwd = REPO_ROOT / "services" / name
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        extra = [str(SHARED_SRC), str(cwd)]
        env["PYTHONPATH"] = os.pathsep.join(extra + [p for p in [env.get("PYTHONPATH")] if p])
        run([python, "-m", "alembic", "upgrade", "head"], cwd=cwd, env=env)
        run([python, "-m", "alembic", "check"], cwd=cwd, env=env)
    print("All Alembic chains upgraded; no drift.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
