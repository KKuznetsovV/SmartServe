from app.modules.ai.services.dispatch import fuzzy_match


def test_fuzzy_match_exact():
    assert fuzzy_match("Pizza", ["Burger", "Pizza", "Salad"]) == 1


def test_fuzzy_match_partial():
    assert fuzzy_match("piz", ["Burger", "Margherita Pizza", "Salad"]) == 1


def test_fuzzy_match_none_hint():
    assert fuzzy_match(None, ["Burger"]) is None


def test_fuzzy_match_no_match():
    assert fuzzy_match("Sushi", ["Burger", "Pizza"]) is None
