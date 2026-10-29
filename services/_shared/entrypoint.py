"""Run Alembic (when present), then exec the container command (uvicorn)."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ATTEMPTS = 30
DELAY_SECONDS = 2


def _upgrade() -> None:
    if not Path("alembic.ini").exists():
        return
    proc = None
    for attempt in range(1, ATTEMPTS + 1):
        proc = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=False)
        if proc.returncode == 0:
            return
        print(f"alembic upgrade failed (attempt {attempt}/{ATTEMPTS}), retrying in {DELAY_SECONDS}s", flush=True)
        time.sleep(DELAY_SECONDS)
    raise SystemExit(proc.returncode if proc is not None else 1)


def main() -> None:
    _upgrade()
    command = sys.argv[1:]
    if not command:
        raise SystemExit("entrypoint: missing command")
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
