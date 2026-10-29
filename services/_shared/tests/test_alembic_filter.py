from types import SimpleNamespace

from smartserve_shared.alembic_filter import owned_include_object


def test_skips_foreign_keys_that_point_at_other_services() -> None:
    include = owned_include_object({"discounts"})
    discounts = SimpleNamespace(name="discounts")
    businesses = SimpleNamespace(name="businesses")
    fk = SimpleNamespace(
        table=discounts,
        elements=[SimpleNamespace(column=SimpleNamespace(table=businesses))],
    )
    assert include(fk, "discounts_business_id_fkey", "foreign_key_constraint", False, None) is False


def test_keeps_foreign_keys_within_owned_tables() -> None:
    include = owned_include_object({"menu_categories", "menu_items"})
    items = SimpleNamespace(name="menu_items")
    categories = SimpleNamespace(name="menu_categories")
    fk = SimpleNamespace(
        table=items,
        elements=[SimpleNamespace(column=SimpleNamespace(table=categories))],
    )
    assert include(fk, None, "foreign_key_constraint", False, None) is True
