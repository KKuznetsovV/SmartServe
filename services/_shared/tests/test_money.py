from decimal import Decimal

from smartserve_shared.money import money, vat_in_inclusive


def test_money_half_up_and_line_qty() -> None:
    assert money("10.10") * 3 == Decimal("30.30")
    assert money(Decimal("10.10") * 3) == Decimal("30.30")
    assert money(Decimal("33.33") * Decimal("15") / Decimal("100")) == Decimal("5.00")
    assert money(Decimal("12.00") * Decimal("1.10")) == Decimal("13.20")
    assert vat_in_inclusive("68", "0.18") == Decimal("10.37")
    assert vat_in_inclusive("90", "0.18") == Decimal("13.73")
    assert vat_in_inclusive("100", "0") == Decimal("0.00")
