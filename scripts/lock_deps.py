"""Compile and check pinned Python requirements for every service.

Usage:
  python scripts/lock_deps.py
  python scripts/lock_deps.py --check
"""

from __future__ import annotations

import argparse
import difflib
import subprocess
import sys
import tempfile
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
COMPILE_COMMAND = "python scripts/lock_deps.py"


def uv_compile(src: Path, dest: Path) -> None:
    cmd = [
        sys.executable,
        "-m",
        "uv",
        "pip",
        "compile",
        str(src.name),
        "-o",
        str(dest),
        "--python-version",
        "3.14",
        "--universal",
        "--custom-compile-command",
        COMPILE_COMMAND,
    ]
    proc = subprocess.run(cmd, cwd=src.parent, text=True, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr or proc.stdout or f"uv pip compile failed for {src}\n")
        raise SystemExit(proc.returncode)


def pairs() -> list[tuple[Path, Path]]:
    out: list[tuple[Path, Path]] = []
    for name in SERVICES:
        service = REPO_ROOT / "services" / name
        out.append((service / "requirements.in", service / "requirements.txt"))
        out.append((service / "requirements-dev.in", service / "requirements-dev.txt"))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if compiled files are stale")
    args = parser.parse_args()
    stale: list[str] = []
    for src, dest in pairs():
        if not src.exists():
            print(f"missing {src.relative_to(REPO_ROOT)}", file=sys.stderr)
            return 1
        if args.check:
            with tempfile.TemporaryDirectory() as tmp:
                compiled = Path(tmp) / dest.name
                uv_compile(src, compiled)
                expected = compiled.read_text(encoding="utf-8")
                actual = dest.read_text(encoding="utf-8") if dest.exists() else ""
                expected_n = expected.replace("\r\n", "\n")
                actual_n = actual.replace("\r\n", "\n")
                if expected_n != actual_n:
                    stale.append(str(dest.relative_to(REPO_ROOT)))
                    if len(stale) == 1:
                        rel = dest.relative_to(REPO_ROOT)
                        sys.stderr.writelines(
                            difflib.unified_diff(
                                actual_n.splitlines(keepends=True),
                                expected_n.splitlines(keepends=True),
                                fromfile=str(rel),
                                tofile=f"{rel} (compiled)",
                                n=2,
                            )
                        )
        else:
            print(f"+ compile {src.relative_to(REPO_ROOT)}")
            uv_compile(src, dest)
    if stale:
        print("pinned requirements are out of date:", file=sys.stderr)
        for path in stale:
            print(f"  {path}", file=sys.stderr)
        print("run: python scripts/lock_deps.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
