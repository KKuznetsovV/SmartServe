"""Audit production deps of the shipped Next.js apps only.

pnpm 11 `audit --filter` still reports the whole lockfile (including apps/pos).
This wrapper runs the production high+ audit, keeps findings whose install
paths start at @smartserve/web or @smartserve/orders, and fails on the rest.

Advisories with no fix on the pinned 15.3.x / zod 3 line are listed in
IGNORED with an expiry. CI fails if an ignore is past its date.

Usage:
  python scripts/pnpm_audit_shipped.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHIPPED_ROOTS = frozenset({"apps__web", "apps__orders"})
FAIL_SEVERITIES = frozenset({"high", "critical"})

# No 15.3.x backport; patched versions are Next.js 15.5.15+ / 15.5.24+ / 15.5.28.
# Stay on 15.3.9 this branch (next lint / config changes land later). Review by 2027-01-31.
_NEXT_15_3_NO_BACKPORT = (
    "GHSA-q4gf-8mx6-v5v3",
    "GHSA-8h8q-6873-q5fj",
    "GHSA-26hh-7cqf-hhc6",
    "GHSA-mg66-mrh9-m8jx",
    "GHSA-c4j6-fc7j-m34r",
    "GHSA-267c-6grr-h53f",
    "GHSA-36qx-fr4f-26g5",
    "GHSA-m99w-x7hq-7vfj",
    "GHSA-89xv-2m56-2m9x",
    "GHSA-p9j2-gv94-2wf4",
    "GHSA-p293-qw3h-jr36",
    "GHSA-2xp9-vwfh-vxw4",
    "GHSA-2464-fhr4-w9xw",
    "GHSA-p3m5-59mp-jv5r",
)

# Zod 3.x has no patched release; fix is >=4.6.6 (breaking). Review by 2027-01-31.
_ZOD_3_NO_FIX = ("GHSA-mrhx-c7xc-m3w5",)

IGNORED: dict[str, date] = {
    **{ghsa: date(2027, 1, 31) for ghsa in _NEXT_15_3_NO_BACKPORT},
    **{ghsa: date(2027, 1, 31) for ghsa in _ZOD_3_NO_FIX},
}


def advisory_id(adv: dict) -> str:
    github = adv.get("github_advisory_id")
    if isinstance(github, str) and github:
        return github
    url = adv.get("url")
    if isinstance(url, str) and "/GHSA-" in url:
        return url.rsplit("/", 1)[-1]
    return str(adv.get("id") or "unknown")


def finding_paths(adv: dict) -> list[str]:
    paths: list[str] = []
    for finding in adv.get("findings") or []:
        paths.extend(finding.get("paths") or [])
    return paths


def path_root(path: str) -> str:
    return path.split(">", 1)[0]


def shipped_paths(paths: list[str]) -> list[str]:
    return [p for p in paths if path_root(p) in SHIPPED_ROOTS]


def run_audit() -> dict:
    pnpm = "pnpm.cmd" if sys.platform == "win32" else "pnpm"
    proc = subprocess.run(
        [
            pnpm,
            "audit",
            "--prod",
            "--audit-level",
            "high",
            "--filter",
            "@smartserve/web",
            "--filter",
            "@smartserve/orders",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    stdout = proc.stdout or ""
    start = stdout.find("{")
    if start < 0:
        sys.stderr.write(proc.stderr or stdout or "pnpm audit produced no JSON\n")
        sys.exit(proc.returncode or 1)
    return json.loads(stdout[start:])


def main() -> int:
    today = datetime.now().date()
    expired = [ghsa for ghsa, expires in sorted(IGNORED.items()) if expires < today]
    if expired:
        print("Expired pnpm audit ignores (re-evaluate or bump the date):")
        for ghsa in expired:
            print(f"  {ghsa} expired {IGNORED[ghsa].isoformat()}")
        return 1

    data = run_audit()
    leftover: list[str] = []
    ignored_hits = 0
    for adv in (data.get("advisories") or {}).values():
        severity = str(adv.get("severity") or "").lower()
        if severity not in FAIL_SEVERITIES:
            continue
        paths = shipped_paths(finding_paths(adv))
        if not paths:
            continue
        ghsa = advisory_id(adv)
        if ghsa in IGNORED:
            ignored_hits += 1
            continue
        leftover.append(
            f"{severity} {adv.get('module_name')} {ghsa} "
            f"patched={adv.get('patched_versions')} paths={paths[:3]}"
        )

    if leftover:
        print("Unignored high/critical findings in @smartserve/web or @smartserve/orders:")
        for line in leftover:
            print(f"  {line}")
        return 1

    print(
        f"pnpm audit shipped apps: clean "
        f"({ignored_hits} ignored 15.3.x/zod-3 findings, expires 2027-01-31)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
