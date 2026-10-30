from decimal import Decimal

from smartserve_shared.money import money


def test_money_half_up_and_line_qty() -> None:
    assert money("10.10") * 3 == Decimal("30.30")
    assert money(Decimal("10.10") * 3) == Decimal("30.30")
    assert money(Decimal("33.33") * Decimal("15") / Decimal("100")) == Decimal("5.00")
    assert money(Decimal("12.00") * Decimal("1.10")) == Decimal("13.20")
