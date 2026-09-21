"""Scorers per format. Every scorer returns a Score that keeps *how* the answer was
parsed, so format failures can be reported separately from wrong answers."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from flembench.schema import Item, letters


@dataclass(frozen=True)
class Score:
    correct: bool | None  # None = not automatically scorable (generation)
    parsed: str | None
    parse: str  # strict | lenient | none | n/a
    contains_gold: bool = False  # extraction/exact: gold appears inside a longer answer


# ---------------------------------------------------------------- multiple choice


def parse_mc(response: str, n_choices: int) -> tuple[str | None, str]:
    valid = "".join(letters(n_choices))
    text = response.strip()
    strict = re.fullmatch(
        rf"(?:antwoord\s*:?\s*)?[\(\[]?([{valid}])[\)\]]?[.:]?", text, flags=re.IGNORECASE
    )
    if strict:
        return strict.group(1).upper(), "strict"
    lenient = re.search(rf"(?<![\w])([{valid}])(?![\w])", text)
    if lenient:
        return lenient.group(1), "lenient"
    return None, "none"


def score_mc(item: Item, response: str) -> Score:
    assert item.choices
    letter, how = parse_mc(response, len(item.choices))
    return Score(correct=letter == item.gold, parsed=letter, parse=how)


# ---------------------------------------------------------------- normalisation

_QUOTES = "\"'“”‘’«»„"
_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        "januari februari maart april mei juni juli augustus september oktober november "
        "december".split()
    )
}


def norm_text(s: str) -> str:
    s = unicodedata.normalize("NFC", s).casefold().strip()
    s = re.sub(r"\s+", " ", s)
    s = s.strip(_QUOTES + " ")
    return s.rstrip(".!?;:, ")


def _as_number(s: str) -> Decimal | None:
    t = re.sub(r"€|(?<![a-z])euros?(?![a-z])|(?<![a-z])eur(?![a-z])", "", s)
    t = t.replace(chr(160), "").replace(" ", "")
    t = t.rstrip(",-").rstrip(".")
    try:
        if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", t):  # Dutch grouping 1.234,56
            return Decimal(t.replace(".", "").replace(",", "."))
        if re.fullmatch(r"-?\d+,\d+", t):  # Dutch decimal 12,5
            return Decimal(t.replace(",", "."))
        if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", t):  # English grouping 1,234.56
            return Decimal(t.replace(",", ""))
        if re.fullmatch(r"-?\d+(\.\d+)?", t):
            return Decimal(t)
    except InvalidOperation:
        return None
    return None


def _as_date(s: str) -> date | None:
    t = s.strip()
    try:
        if m := re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", t):
            return date(int(m[3]), int(m[2]), int(m[1]))
        if m := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", t):
            return date(int(m[1]), int(m[2]), int(m[3]))
        if m := re.fullmatch(r"(\d{1,2}) ([a-z]+) (\d{4})", t):
            if m[2] in _MONTHS:
                return date(int(m[3]), _MONTHS[m[2]], int(m[1]))
    except ValueError:
        return None
    return None


def canonical(s: str) -> str:
    """Canonical form for extraction: dates -> ISO, numbers -> plain decimal,
    otherwise normalised text with internal spaces removed (postcodes, IDs)."""
    t = norm_text(s)
    if (d := _as_date(t)) is not None:
        return d.isoformat()
    if (n := _as_number(t)) is not None:
        return format(n.normalize(), "f")
    return t.replace(" ", "")


# ---------------------------------------------------------------- exact / extraction


def _score_against(item: Item, response: str, norm) -> Score:
    golds = {norm(g) for g in [item.gold, *item.accepted_variants]}
    got = norm(response)
    if got in golds:
        return Score(correct=True, parsed=got, parse="strict")
    haystack = norm_text(response)
    contains = any(
        norm_text(g) and norm_text(g) in haystack for g in [item.gold, *item.accepted_variants]
    )
    return Score(correct=False, parsed=got, parse="strict", contains_gold=contains)


def score_exact(item: Item, response: str) -> Score:
    return _score_against(item, response, norm_text)


def score_extract(item: Item, response: str) -> Score:
    return _score_against(item, response, canonical)


def score_generation(item: Item, response: str) -> Score:
    return Score(correct=None, parsed=None, parse="n/a")


SCORERS = {
    "mc_letter": score_mc,
    "norm_exact": score_exact,
    "norm_extract": score_extract,
    "rubric": score_generation,
}


def score(item: Item, response: str) -> Score:
    return SCORERS[item.scoring_method or "mc_letter"](item, response)
