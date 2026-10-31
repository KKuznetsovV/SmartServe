"""Normalized name matching for items and categories (`name` and `name_he`)."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

_NIQQUD = re.compile(r"[\u0591-\u05C7]")
_PUNCT = re.compile(r"[^\w\s]", flags=re.UNICODE)


class MatchError(Exception):
    def __init__(self, hint: str, suggestions: list[str]):
        super().__init__(hint)
        self.hint = hint
        self.suggestions = suggestions[:3]


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).strip().casefold()
    text = _NIQQUD.sub("", text)
    text = _PUNCT.sub("", text)
    return " ".join(text.split())


def _labels(record: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    labels: list[str] = []
    for key in keys:
        raw = record.get(key)
        if isinstance(raw, str) and raw.strip():
            labels.append(raw)
    return labels


def suggestions_for(
    hint: str, records: list[dict[str, Any]], *, keys: tuple[str, ...] = ("name", "nameHe")
) -> list[str]:
    needle = normalize(hint)
    scored: list[tuple[float, str]] = []
    seen: set[str] = set()
    for record in records:
        primary = record.get("name") or next(iter(_labels(record, keys)), "")
        if not primary or primary in seen:
            continue
        best = 0.0
        for label in _labels(record, keys):
            hay = normalize(label)
            if not hay:
                continue
            best = max(best, SequenceMatcher(None, needle, hay).ratio())
            if needle and (needle in hay or hay in needle):
                best = max(best, 0.85)
        scored.append((best, primary))
        seen.add(primary)
    scored.sort(key=lambda row: row[0], reverse=True)
    return [name for score, name in scored if score > 0][:3]


def match_index(
    hint: str | None,
    records: list[dict[str, Any]],
    *,
    keys: tuple[str, ...] = ("name", "nameHe"),
) -> int | None:
    """Index of the best record, or None when `hint` is empty. Raises MatchError on no match."""
    if not hint or not str(hint).strip():
        return None
    needle = normalize(str(hint))
    if not needle:
        return None
    exact: list[int] = []
    partial: list[int] = []
    for i, record in enumerate(records):
        for label in _labels(record, keys):
            hay = normalize(label)
            if not hay:
                continue
            if hay == needle:
                exact.append(i)
                break
            if needle in hay or hay in needle:
                partial.append(i)
                break
    if exact:
        return exact[0]
    if partial:
        return partial[0]
    raise MatchError(str(hint).strip(), suggestions_for(str(hint), records, keys=keys))
