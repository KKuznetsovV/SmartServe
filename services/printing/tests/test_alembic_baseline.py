from pathlib import Path


def test_printing_baseline_owns_printer_tables():
    root = Path(__file__).resolve().parents[1]
    baseline = (root / "alembic/versions/0001_baseline.py").read_text(encoding="utf-8")
    env = (root / "alembic/env.py").read_text(encoding="utf-8")
    for table in ("printers", "printer_routes", "print_jobs"):
        assert table in baseline
    assert "def downgrade" in baseline
    assert "alembic_version_printing" in env
    assert "PRINTING_OWNED_TABLES" in env
