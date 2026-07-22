"""Detect near-duplicate Paperless correspondent names before creating new ones."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Tokens shorter than this are ignored for overlap scoring (gmbh, co, ag, …).
_MIN_SIGNIFICANT_TOKEN_LEN = 4
# Require at least one longer shared token so weak overlaps do not merge.
_MIN_CORE_TOKEN_LEN = 5
_DEFAULT_JACCARD_THRESHOLD = 0.5

_LEGAL_SUFFIXES = frozenset(
    {
        "gmbh",
        "ag",
        "kg",
        "ohg",
        "ug",
        "eg",
        "ek",
        "gbr",
        "mbh",
        "co",
        "und",
        "and",
        "the",
        "der",
        "die",
        "das",
        "von",
        "van",
    }
)

_ABBREVIATIONS = {
    "stb": "steuerberater",
    "stbin": "steuerberaterin",
    "ra": "rechtsanwalt",
    "rain": "rechtsanwaeltin",
    "dr": "doktor",
    "dipl": "diplom",
    "ing": "ingenieur",
    "kfr": "kaufmann",
    "kfrn": "kauffrau",
}

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_UMLAUT_MAP = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
)


def normalize_correspondent_name(name: str) -> str:
    """Lowercase, strip diacritics/umlauts, and collapse punctuation to spaces."""
    text = unicodedata.normalize("NFKC", name or "").casefold().translate(_UMLAUT_MAP)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return _NON_ALNUM_RE.sub(" ", text).strip()


def correspondent_name_tokens(name: str) -> frozenset[str]:
    """Tokenize a correspondent name with abbreviation expansion."""
    normalized = normalize_correspondent_name(name)
    if not normalized:
        return frozenset()
    tokens: set[str] = set()
    for raw in normalized.split():
        token = _ABBREVIATIONS.get(raw, raw)
        if token in _LEGAL_SUFFIXES:
            continue
        if len(token) < _MIN_SIGNIFICANT_TOKEN_LEN:
            continue
        tokens.add(token)
    return frozenset(tokens)


def correspondent_similarity_score(
    left_name: str,
    right_name: str,
) -> float:
    """
    Score name similarity in [0, 1].

    Prefers containment of the shorter token set; otherwise uses Jaccard overlap.
    Returns 0 when there is no shared core token (length >= 5).
    """
    left = correspondent_name_tokens(left_name)
    right = correspondent_name_tokens(right_name)
    if not left or not right:
        return 0.0

    shared = left & right
    if not any(len(token) >= _MIN_CORE_TOKEN_LEN for token in shared):
        return 0.0

    if left <= right or right <= left:
        return 1.0

    union = left | right
    return len(shared) / len(union)


def find_duplicate_correspondent(
    proposed_name: str,
    correspondents: list[dict[str, Any]],
    *,
    threshold: float = _DEFAULT_JACCARD_THRESHOLD,
) -> dict[str, Any] | None:
    """
    Return the best existing correspondent that looks like a duplicate.

    Returns None when no candidate clears the threshold, or when multiple
    candidates tie at the best score (ambiguous — prefer review over merge).
    """
    proposed_tokens = correspondent_name_tokens(proposed_name)
    if not proposed_tokens:
        return None

    best_score = 0.0
    best: list[dict[str, Any]] = []
    for corr in correspondents:
        name = str(corr.get("name") or "")
        if not name:
            continue
        score = correspondent_similarity_score(proposed_name, name)
        if score < threshold:
            continue
        if score > best_score:
            best_score = score
            best = [corr]
        elif score == best_score:
            best.append(corr)

    if len(best) == 1:
        return best[0]
    return None


def merge_correspondent_match(existing_match: str | None, new_match: str | None) -> str | None:
    """Merge two Paperless regex match strings with alternation when needed."""
    existing = (existing_match or "").strip()
    incoming = (new_match or "").strip()
    if not incoming:
        return existing or None
    if not existing:
        return incoming
    if incoming in existing or existing in incoming:
        return existing if len(existing) >= len(incoming) else incoming
    return f"(?:{existing})|(?:{incoming})"
