from collections import Counter

import pytest
from pydantic import ValidationError

from flembench.items import build_items, check_pairs, load_dir, shuffle_choices
from flembench.schema import Split, letters
from tests.conftest import pair_doc


def test_pair_members_share_gold_position(pair_items):
    be, nl = pair_items
    assert be.id == "a1-9999-be" and nl.id == "a1-9999-nl"
    assert be.gold == nl.gold
    assert be.choices[letters(4).index(be.gold)] == "juist"
    assert nl.choices[letters(4).index(nl.gold)] == "goed"
    assert be.track == "A" and be.scoring_method == "mc_letter"


def test_shuffle_is_deterministic_and_balanced():
    assert shuffle_choices("k", ["a", "b", "c", "d"]) == shuffle_choices("k", ["a", "b", "c", "d"])
    golds = Counter(shuffle_choices(f"a1-{i:04d}", list("abcd"))[1] for i in range(4000))
    assert all(900 < n < 1100 for n in golds.values()), golds


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"nl": None}, "needs both"),
        ({"category": "Z9"}, "unknown category"),
        ({"match_basis": None}, "match_basis"),
        ({"be": {"prompt": "p", "choices": ["a", "a", "b"]}}, "distinct"),
    ],
)
def test_invalid_pairs_rejected(overrides, message):
    doc = pair_doc(**overrides)
    doc = {k: v for k, v in doc.items() if v is not None}
    with pytest.raises((ValueError, ValidationError), match=message):
        build_items(doc)


def test_mc_gold_must_not_be_set_by_author():
    doc = pair_doc()
    doc["be"] = {**doc["be"], "gold": "A"}
    with pytest.raises(ValueError, match="correct answer first"):
        build_items(doc)


def test_track_b_requires_valid_as_of():
    doc = pair_doc(
        pair_id="b1-0001", category="B1", subcategory=None, match_basis="functional_analogue"
    )
    with pytest.raises(ValidationError, match="valid_as_of"):
        build_items(doc)
    doc["valid_as_of"] = "2026-09-21"
    assert len(build_items(doc)) == 2


def test_llm_drafted_requires_drafted_by():
    with pytest.raises(ValidationError, match="drafted_by"):
        build_items(pair_doc(provenance="llm_drafted_human_verified"))


def test_unpaired_item():
    [it] = build_items(
        {
            "id": "b2-0001",
            "category": "B2",
            "format": "exact",
            "valid_as_of": "2026-09-21",
            "author": "t",
            "provenance": "human_written",
            "be": {"prompt": "p", "gold": "3"},
        }
    )
    assert it.pair_id is None and it.scoring_method == "norm_exact"


def test_check_pairs_detects_mismatch(pair_items):
    be, nl = pair_items
    nl2 = nl.model_copy(update={"subcategory": "A1b"})
    assert any("subcategory" in e for e in check_pairs([be, nl2]))
    assert any("duplicate" in e for e in check_pairs([be, be]))


def test_load_dir_skips_templates_and_enforces_split(tmp_path):
    (tmp_path / "_templates").mkdir()
    (tmp_path / "_templates" / "t.yaml").write_text("not: [valid", encoding="utf-8")
    (tmp_path / "A1").mkdir()
    import yaml

    (tmp_path / "A1" / "ok.yaml").write_text(yaml.safe_dump(pair_doc()), encoding="utf-8")
    (tmp_path / "A1" / "held.yaml").write_text(
        yaml.safe_dump(pair_doc(pair_id="a1-0002", split="heldout")), encoding="utf-8"
    )
    res = load_dir(tmp_path, Split.PUBLIC)
    assert len(res.items) == 4
    assert any("heldout" in e for e in res.errors)


def test_repo_templates_are_valid_yaml():
    from pathlib import Path

    import yaml

    for p in (Path(__file__).parents[1] / "items" / "_templates").glob("*.yaml"):
        assert isinstance(yaml.safe_load(p.read_text(encoding="utf-8")), dict), p
