from flembench import curate
from flembench import glosses as gl


def test_export_includes_variety_but_not_claude_glosses(tmp_path):
    paths = gl.export([("w0001", "be", "zwalpen"), ("w0002", "nl", "kliko")], root=tmp_path)
    assert paths[0].read_text(encoding="utf-8") == "w0001|BE|zwalpen\nw0002|NL|kliko\n"
    assert "Do not guess" in (tmp_path / "PROMPT.md").read_text(encoding="utf-8")


def test_parse_and_import(tmp_path):
    out, problems = gl.parse_output("```\nw0001|klotsen; over de rand golven\nw0002|?\njunk\n```")
    assert out == {"w0001": "klotsen; over de rand golven", "w0002": ""}
    assert len(problems) == 1
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "gemini-3.8-flash__01.txt").write_text(
        "w0001|klotsen\nw0002|?\n", encoding="utf-8"
    )
    rows = {
        ("be", "zwalpen"): {"variety": "be", "word": "zwalpen", "claude_gloss": "klotsen"},
        ("nl", "kliko"): {"variety": "nl", "word": "kliko", "claude_gloss": ""},
    }
    ids = {"w0001": ("be", "zwalpen"), "w0002": ("nl", "kliko")}
    merged, stats = gl.import_results(rows, ids, root=tmp_path)
    assert merged[("be", "zwalpen")]["gemini_gloss"] == "klotsen"
    assert merged[("nl", "kliko")]["gemini_gloss"] == "?"
    assert stats["filled"] == 2 and stats["models"] == ["gemini-3.8-flash"]


def test_draft_prefers_claude_then_gemini_never_unknown():
    assert gl.draft_for({"claude_gloss": "klotsen"}) == ("klotsen", "claude-opus-5")
    row = {"claude_gloss": "", "gemini_gloss": "rolcontainer", "gemini_model": "g"}
    assert gl.draft_for(row) == ("rolcontainer", "g")
    assert gl.draft_for({"claude_gloss": "", "gemini_gloss": "?"}) == ("", "")
    assert gl.draft_for(None) == ("", "")


def test_decision_records_gloss_source():
    s = curate.Session.create([curate.Candidate("be", "zwalpen")], {}, seed=0)
    row = s.decide(
        "k",
        register="tussentaal",
        gloss="klotsen",
        gloss_source="claude-opus-5 (accepted by author)",
    )
    assert row["gloss_source"].startswith("claude-opus-5")
    s2 = curate.Session.create([curate.Candidate("be", "x")], {}, seed=0)
    assert s2.decide("t", gloss_source="ignored")["gloss_source"] == ""


def test_repo_glosses_cover_all_candidates():
    rows = gl.load()
    assert len(rows) == 1081
    assert all(
        r["claude_confidence"] in {"high", "medium", "low", "unknown"} for r in rows.values()
    )
