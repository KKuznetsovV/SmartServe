from pathlib import Path


def test_staff_baseline_owns_shifts_only():
    root = Path(__file__).resolve().parents[1]
    baseline = (root / "alembic/versions/0001_baseline.py").read_text(encoding="utf-8")
    env = (root / "alembic/env.py").read_text(encoding="utf-8")
    assert "shifts" in baseline
    assert "def downgrade" in baseline
    assert "alembic_version_staff" in env
    assert "STAFF_OWNED_TABLES" in env
