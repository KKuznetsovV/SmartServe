import pytest

from app.modules.ai.services.match import MatchError, match_index, normalize


def test_normalize_strips_niqqud_and_punctuation():
    assert normalize("  הַמְבּוּרְגֶר!! ") == normalize("המבורגר")
    assert normalize("Drinks") == normalize("drinks")


def test_match_index_hebrew_name():
    records = [
        {"id": "1", "name": "Burger", "nameHe": "המבורגר"},
        {"id": "2", "name": "Salmon Fillet", "nameHe": "פילה סלמון"},
    ]
    assert records[match_index("המבורגר", records)]["id"] == "1"
    assert records[match_index("salmon", records)]["id"] == "2"


def test_match_index_no_match_suggestions():
    records = [
        {"id": "1", "name": "Cola", "nameHe": "קולה"},
        {"id": "2", "name": "Lemonade", "nameHe": "לימונדה"},
        {"id": "3", "name": "Burger", "nameHe": "המבורגר"},
    ]
    with pytest.raises(MatchError) as exc:
        match_index("סושי", records)
    assert len(exc.value.suggestions) <= 3
