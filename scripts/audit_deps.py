"""Fail when pip-audit reports high or critical findings for a service.

Usage:
  python scripts/audit_deps.py
"""

from __future__ import annotations

import json
import os
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
FAIL_SEVERITIES = {"HIGH", "CRITICAL"}


def pip_requirement_lines(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-e "):
            continue
        lines.append(stripped)
    return lines


def vuln_severity(vuln: dict) -> str:
    explicit = vuln.get("severity")
    if isinstance(explicit, str) and explicit:
        return explicit.upper()
    return "UNKNOWN"


def pip_audit_service(name: str) -> list[str]:
    req = REPO_ROOT / "services" / name / "requirements.txt"
    packages = pip_requirement_lines(req)
    if not packages:
        return []
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as handle:
        handle.write("\n".join(packages) + "\n")
        tmp = handle.name
    try:
        print(f"+ pip-audit ({name})", flush=True)
        proc = subprocess.run(
            [sys.executable, "-m", "pip_audit", "-r", tmp, "--format", "json", "--progress-spinner", "off"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
    finally:
        os.unlink(tmp)
    if proc.returncode not in (0, 1):
        detail = (proc.stderr or proc.stdout or "")[-300:]
        return [f"{name}: pip-audit failed: {detail}"]
    payload_text = (proc.stdout or "").strip()
    if not payload_text:
        return []
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return [f"{name}: pip-audit produced non-JSON output"]
    deps = payload.get("dependencies", []) if isinstance(payload, dict) else payload
    findings: list[str] = []
    for dep in deps or []:
        for vuln in dep.get("vulns") or []:
            severity = vuln_severity(vuln)
            if severity not in FAIL_SEVERITIES:
                continue
            ident = vuln.get("id") or "unknown"
            findings.append(f"{name}: {dep.get('name')} {dep.get('version')} {ident} ({severity})")
    return findings


def main() -> int:
    findings: list[str] = []
    for name in SERVICES:
        findings.extend(pip_audit_service(name))
    if findings:
        print("High/critical Python dependency findings:")
        for line in findings:
            print(f"  {line}")
        return 1
    print("No high or critical Python dependency findings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
