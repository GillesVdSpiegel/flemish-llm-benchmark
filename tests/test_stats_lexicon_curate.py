import pandas as pd
import pytest

from flembench import curate, lexicon, stats
from flembench.prompts import render

# ------------------------------------------------------------------ stats


def _scores(pairs):
    rows = []
    for i, (be, nl) in enumerate(pairs):
        rows += [
            {"pair_id": f"p{i}", "variety": "be", "correct": be},
            {"pair_id": f"p{i}", "variety": "nl", "correct": nl},
        ]
    return pd.DataFrame(rows)


def test_paired_gap_direction_and_counts():
    g = stats.paired_gap(_scores([(0, 1)] * 30 + [(1, 1)] * 60 + [(1, 0)] * 10))
    assert g.n_pairs == 100 and g.gap == pytest.approx(-0.2)
    assert (g.be_only, g.nl_only) == (10, 30)
    assert g.ci_low < -0.2 < g.ci_high < 0 and g.p_mcnemar < 0.01


def test_paired_gap_null():
    g = stats.paired_gap(_scores([(1, 0)] * 10 + [(0, 1)] * 10 + [(1, 1)] * 30))
    assert g.gap == 0 and g.ci_low < 0 < g.ci_high and g.p_mcnemar == 1.0


def test_ci_halfwidth_matches_design_table():
    assert stats.ci_halfwidth(50, 0.2) == pytest.approx(0.124, abs=0.001)
    assert stats.ci_halfwidth(100, 0.1) == pytest.approx(0.062, abs=0.001)


# ------------------------------------------------------------------ lexicon


def _cands(rows):
    return pd.DataFrame(rows, columns=["spelling", "p_own", "own_gap"])


def test_match_pairs_respects_tolerances():
    be = _cands([("a", 0.90, 0.50), ("b", 0.95, 0.40), ("c", 0.80, 0.70)])
    nl = _cands([("x", 0.91, 0.52), ("y", 0.95, 0.41), ("z", 0.60, 0.10)])
    p = lexicon.match_pairs(be, nl)
    assert set(zip(p.be_word, p.nl_word, strict=True)) == {("a", "x"), ("b", "y")}


def test_flag_inflections():
    c = pd.DataFrame({"spelling": ["tornooi", "tornooien", "kot"]})
    f = lexicon.flag_inflections(c)
    assert f.set_index("spelling").loc["tornooien", "inflection_of"] == "tornooi"
    assert pd.isna(f.set_index("spelling").loc["kot", "inflection_of"])


# ------------------------------------------------------------------ curation


def _cand_list():
    return [curate.Candidate("be", f"b{i}") for i in range(3)] + [
        curate.Candidate("nl", f"n{i}") for i in range(3)
    ]


def test_session_interleaves_and_resumes():
    s = curate.Session.create(_cand_list(), {}, seed=1)
    assert [c.variety for c in s.queue] == ["be", "nl"] * 3
    first = s.current
    s.decide("k", register="standard", gloss="betekenis")
    s2 = curate.Session.create(_cand_list(), s.decided, seed=1)
    assert first not in s2.queue and len(s2.queue) == 5


def test_undo_and_skip():
    cands = _cand_list()
    s = curate.Session.create(cands, {}, seed=0)
    by_key = {(c.variety, c.word): c for c in cands}
    first = s.current
    s.decide("t")
    assert s.undo(by_key) == (first.variety, first.word) and s.current == first
    s.skip()
    assert s.queue[-1] == first


def test_decisions_roundtrip_has_no_prevalence(tmp_path):
    s = curate.Session.create(_cand_list(), {}, seed=0)
    s.decide("k", register="tussentaal", gloss="zin, trek")
    s.decide("a")
    path = tmp_path / "d.csv"
    curate.save_decisions(s.decided, path)
    loaded = curate.load_decisions(path)
    assert loaded == s.decided
    header = path.read_text(encoding="utf-8").splitlines()[0]
    assert "p_own" not in header and "prevalence" not in header


# ------------------------------------------------------------------ prompts


def test_render_mc(pair_items):
    system, user = render(pair_items[0])
    assert "A. " in user and "D. " in user
    assert user.endswith("(A, B, C of D).")
    assert system == render(pair_items[1])[0]
