import csv

from flembench import prefilter


def _setup(tmp_path, n=40):
    cands = [("be", f"b{i}") for i in range(n // 2)] + [("nl", f"n{i}") for i in range(n // 2)]
    paths = prefilter.export(cands, batch_size=15, root=tmp_path)
    words = prefilter.load_words(tmp_path)
    return paths, words


def _write(tmp_path, model, batch, verdicts):
    d = tmp_path / "results"
    d.mkdir(exist_ok=True)
    (d / f"{model}__{batch}.txt").write_text(
        "\n".join(f"{i};{c}" for i, c in verdicts.items()), encoding="utf-8"
    )


def test_export_hides_variety_and_mixes_batches(tmp_path):
    paths, words = _setup(tmp_path)
    assert [p.name for p in paths] == ["01.txt", "02.txt", "03.txt"]
    first = paths[0].read_text(encoding="utf-8").splitlines()
    assert all(line.count(";") == 1 and "be" not in line.split(";")[0] for line in first)
    varieties = {words[line.split(";")[0]].variety for line in first}
    assert varieties == {"be", "nl"}
    assert "Do NOT judge meaning" in (tmp_path / "PROMPT.md").read_text(encoding="utf-8")


def test_parse_output_tolerates_fences_and_flags_junk():
    out, problems = prefilter.parse_output(
        "```\nw0001;NONE\nw0002 ; brand\nhello\nw0003;MAYBE\n```"
    )
    assert out == {"w0001": "NONE", "w0002": "BRAND"}
    assert len(problems) == 2


def test_only_unanimous_non_none_with_two_models():
    v = {
        "a": {"w1": "BRAND", "w2": "BRAND", "w3": "NONE", "w4": "ABBR"},
        "b": {"w1": "BRAND", "w2": "NAME", "w3": "NONE"},
    }
    assert prefilter.unanimous(v) == {"w1": ("BRAND", ["a", "b"])}  # w4: only one model


def test_apply_never_overrides_author_and_holds_back_audit(tmp_path):
    paths, words = _setup(tmp_path, n=120)
    ids = sorted(words)
    flagged = ids[:60]
    for batch, p in enumerate(paths, start=1):
        batch_ids = [line.split(";")[0] for line in p.read_text(encoding="utf-8").splitlines()]
        v = {i: ("ABBR" if i in flagged else "NONE") for i in batch_ids}
        for model in ("claude", "gpt"):
            _write(tmp_path, model, f"{batch:02d}", v)
    author_word = words[flagged[0]]
    author = {
        (author_word.variety, author_word.word): {
            "variety": author_word.variety, "word": author_word.word, "decision": "keep",
            "decided_by": "author",
        }
    }  # fmt: skip
    decided, stats = prefilter.apply(author, root=tmp_path)
    assert stats["unanimous_flags"] == 60 and stats["held_back_for_blind_audit"] == 6
    assert decided[(author_word.variety, author_word.word)]["decision"] == "keep"
    auto = [r for r in decided.values() if r.get("decided_by") == "llm_prefilter"]
    assert all(r["decision"] == "move_to_b1" for r in auto)
    with (tmp_path / "audit.csv").open(encoding="utf-8") as f:
        audit = {(r["variety"], r["word"]) for r in csv.DictReader(f)}
    assert not audit & {k for k, r in decided.items() if r.get("decided_by") == "llm_prefilter"}
    assert len(auto) + len(audit) + 1 >= 60  # author word may or may not be in the audit
    # Re-import is idempotent.
    again, _ = prefilter.apply(decided, root=tmp_path)

    def strip(d):
        return {k: {f: x for f, x in v.items() if f != "decided_at"} for k, v in d.items()}

    assert strip(again) == strip(decided)


def test_report_agreement(tmp_path):
    (tmp_path / "audit.csv").write_text(
        "id,variety,word,llm_category,models\nw1,be,kmo,ABBR,a\nw2,nl,kliko,BRAND,a\n",
        encoding="utf-8",
    )
    decided = {
        ("be", "kmo"): {"decision": "move_to_b1"},
        ("nl", "kliko"): {"decision": "keep"},
    }
    r = prefilter.report(decided, root=tmp_path)
    assert r["agreement"] == "1/2" and "kliko" in r["disagreements"][0]


def test_sparse_output_brand_not_applied_and_skips_go_to_author(tmp_path):
    paths, words = _setup(tmp_path, n=30)
    batch = [line.split(";")[0] for line in paths[0].read_text(encoding="utf-8").splitlines()]
    abbr, brand, name = batch[0], batch[1], batch[2]
    # Model a lists three words; model b agrees but skipped `name` (-> NONE for b).
    _write(tmp_path, "a", "01", {abbr: "ABBR", brand: "BRAND", name: "NAME"})
    _write(tmp_path, "b", "01", {abbr: "ABBR", brand: "BRAND"})
    (tmp_path / "results" / "c__02.txt").write_text("NONE\n", encoding="utf-8")
    verdicts, problems = prefilter.load_results(tmp_path)
    assert verdicts["a"][batch[5]] == "NONE" and not problems
    assert all(v == "NONE" for v in verdicts["c"].values()) and len(verdicts["c"]) == 15
    decided, stats = prefilter.apply({}, root=tmp_path)
    assert stats["unanimous_flags"] == 1  # only the ABBR: brand never applied, name not unanimous
    assert stats["unanimous_brand_flags_left_to_author"] == 1
    w = words[abbr]
    # A single auto-decision falls entirely in the blind audit (minimum audit size).
    assert (w.variety, w.word) not in decided and stats["held_back_for_blind_audit"] == 1


def test_prefilter_can_only_route_never_reject_or_accept():
    auto = {d for d in prefilter.CATEGORY_DECISION.values() if d}
    assert auto <= prefilter.ALLOWED_AUTO_DECISIONS == {"move_to_b1"}
