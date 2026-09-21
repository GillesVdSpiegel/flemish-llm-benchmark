import pytest

from flembench.items import build_items
from flembench.scoring import canonical, norm_text, parse_mc, score


@pytest.mark.parametrize(
    "response, expected",
    [
        ("B", ("B", "strict")),
        (" b. ", ("B", "strict")),
        ("(C)", ("C", "strict")),
        ("Antwoord: D", ("D", "strict")),
        ("Het juiste antwoord is B, want ...", ("B", "lenient")),
        ("Geen idee", (None, "none")),
        ("E", (None, "none")),
    ],
)
def test_parse_mc(response, expected):
    assert parse_mc(response, 4) == expected


def test_score_mc(pair_items):
    be, _ = pair_items
    assert score(be, be.gold).correct
    wrong = next(letter for letter in "ABCD" if letter != be.gold)
    s = score(be, wrong)
    assert s.correct is False and s.parse == "strict"


@pytest.mark.parametrize(
    "a, b",
    [
        ("€ 1.234,56", "1234.56"),
        ("1234,56 EUR", "1234.56"),
        ("1.234,56 euro", "1234.56"),
        ("12,50", "12.5"),
        ("31/12/2026", "2026-12-31"),
        ("31-12-2026", "2026-12-31"),
        ("31 december 2026", "2026-12-31"),
        ("2000 Antwerpen", "2000antwerpen"),
        ("1234 AB", "1234ab"),
    ],
)
def test_canonical_equivalences(a, b):
    assert canonical(a) == canonical(b)


def test_canonical_follows_dutch_number_convention():
    assert canonical("1.234") == "1234"  # period = thousands separator in Dutch
    assert canonical("12,5") == "12.5" != canonical("125")


def test_norm_text():
    assert norm_text('  "Het OCMW."  ') == "het ocmw"


def _item(fmt, gold, variants=()):
    [it] = build_items(
        {
            "id": "b2-0009",
            "category": "B2",
            "format": fmt,
            "valid_as_of": "2026-09-21",
            "author": "t",
            "provenance": "human_written",
            "be": {"prompt": "p", "gold": gold, "accepted_variants": list(variants)},
        }
    )
    return it


def test_extraction_and_contains_flag():
    it = _item("extraction", "15/10/2026")
    assert score(it, "15 oktober 2026").correct
    s = score(it, "De deadline is 15/10/2026.")
    assert s.correct is False and s.contains_gold


def test_exact_with_variants():
    it = _item("exact", "schepen", ["schepen van financiën"])
    assert score(it, "Schepen.").correct
    assert score(it, "schepen van Financiën").correct
    assert not score(it, "wethouder").correct
