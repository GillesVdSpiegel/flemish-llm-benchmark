from flembench import generate
from flembench.generate import Entry, clean_gloss, pick_distractors, resembles


def test_clean_gloss_removes_formatting_giveaways():
    assert (
        clean_gloss("wiezen (kaartspel)", "wiezen") == "wiezen (kaartspel)"
    )  # flagged as overlap instead
    assert resembles("wiezen", "wiezen (kaartspel)")
    assert clean_gloss("kaartspel (wiezen)", "wiezen") == "kaartspel"
    assert clean_gloss("op de bonnefooi: op goed geluk", "bonnefooi") == "op goed geluk"
    assert clean_gloss("bakwijze van vlees (saignant, à point)", "cuisson") == (
        "bakwijze van vlees (saignant, à point)"
    )


def test_resembles():
    assert resembles("bakkerin", "bakkersvrouw")
    assert resembles("halvarine", "halvarine")
    assert not resembles("zwalpen", "klotsen")
    assert not resembles("kot", "studentenkamer")


def _pool():
    glosses = [
        "klotsen", "koelkast", "studentenkamer", "rommel", "zin, trek", "oma", "opa",
        "portemonnee", "stomerij", "kermis", "zin hebben in eten", "kleine ruimte",
    ]  # fmt: skip
    return [Entry("be", f"w{i}", g, "claude", "bulk", "unspecified") for i, g in enumerate(glosses)]


def test_distractors_are_deterministic_unrelated_and_distinct():
    target = Entry("be", "goesting", "zin, trek", "claude", "bulk", "unspecified")
    pool = _pool()
    a = pick_distractors(target, pool, {("be", "goesting")}, seed=1)
    assert a == pick_distractors(target, pool, {("be", "goesting")}, seed=1)
    assert len(set(a)) == 3 and "zin, trek" not in a
    assert all(not resembles("goesting", g) for g in a)


def test_build_pairs_share_template_and_split_is_seeded():
    decisions = {
        ("be", "zwalpen"): {"decision": "keep", "gloss": "klotsen", "decided_by": "author"},
        ("nl", "kliko"): {"decision": "keep", "gloss": "rolcontainer", "decided_by": "bulk"},
        **{
            ("be", f"x{i}"): {"decision": "keep", "gloss": g, "decided_by": "bulk"}
            for i, g in enumerate(["oma", "kermis", "stomerij", "portemonnee", "rommel", "opa"])
        },
    }
    pairs = [{"be_word": "zwalpen", "nl_word": "kliko"}]
    [doc] = generate.build(decisions, pairs, seed=0)
    assert doc["be"]["prompt"].endswith("zoals het in België gebruikt wordt?")
    assert doc["nl"]["prompt"].endswith("zoals het in Nederland gebruikt wordt?")
    assert doc["be"]["choices"][0] == "klotsen" and doc["be"]["reviewed_by"] == ["author"]
    assert doc["nl"]["reviewed_by"] == [] and doc["subcategory"] == "A1a-clean"
    assert doc == generate.build(decisions, pairs, seed=0)[0]


def test_sample_seed_is_namespaced_against_the_heldout_draw():
    """A plain Random(0) sample over the same population reproduces generate.build's held-out
    draw; the CLI must not do that (regression: variance sample was 92% held-out)."""
    import random

    pairs = [f"a1a-{i:04d}" for i in range(1, 494)]
    heldout_idx = set(random.Random(0).sample(range(len(pairs)), 99))
    heldout = {pairs[i] for i in heldout_idx}
    naive = set(random.Random(0).sample(pairs, 60))
    namespaced = set(random.Random("sample_pairs-0").sample(pairs, 60))
    assert len(naive & heldout) > 50  # the collision this guards against
    assert len(namespaced & heldout) < 25  # roughly the 20% you would expect
