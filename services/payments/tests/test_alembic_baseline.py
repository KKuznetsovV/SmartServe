from pathlib import Path


def test_payments_baseline_owns_payments_only():
    root = Path(__file__).resolve().parents[1]
    baseline = (root / "alembic/versions/0001_baseline.py").read_text(encoding="utf-8")
    env = (root / "alembic/env.py").read_text(encoding="utf-8")
    assert '"payments"' in baseline
    assert "def downgrade" in baseline
    assert "alembic_version_payments" in env
    assert "PAYMENTS_OWNED_TABLES" in env
