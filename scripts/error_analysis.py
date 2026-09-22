"""Error analysis for the A1 lexicon track. Reads only cached results; calls no model.

    uv run python scripts/error_analysis.py            # writes analysis/error_analysis.md

Prevalence values (CC BY-NC) are read from the gitignored derived file and only reported in
aggregate bins, never per item.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flembench import curate, items, lexicon  # noqa: E402
from flembench.schema import Split  # noqa: E402

OUT = ROOT / "analysis" / "error_analysis.md"
MIN_ITEMS_COMPLETE = 700


def load() -> tuple[pd.DataFrame, dict]:
    scores = pd.read_csv(ROOT / "runs" / "scores.csv")
    scores = scores[(scores.repeat == 0) & scores.correct.notna()]
    complete = scores.groupby("model").size()
    scores = scores[scores.model.isin(complete[complete > MIN_ITEMS_COMPLETE].index)]
    its = {i.id: i for i in items.load_dir(ROOT / "items", Split.PUBLIC).items}
    scores["marker"] = scores.item_id.map(lambda i: its[i].marker)
    scores["chosen"] = [
        its[r.item_id].choices["ABCD".index(r.parsed)]
        if isinstance(r.parsed, str) and r.parsed in "ABCD"
        else None
        for r in scores.itertuples()
    ]
    scores["gold_text"] = scores.item_id.map(lambda i: its[i].choices["ABCD".index(its[i].gold)])
    return scores, its


def section(title: str, body: str) -> str:
    return f"\n## {title}\n\n{body}\n"


def main() -> None:
    s, its = load()
    models = sorted(s.model.unique())
    out = [f"# Error analysis — A1 lexicon track\n\nModels: {', '.join(models)}. "
           f"Items: {s.item_id.nunique()} (public split, first run).\n"]  # fmt: skip

    # 1. Items everyone gets wrong: usually a questionable gold answer.
    per_item = s.groupby("item_id").correct.agg(["sum", "count"])
    allwrong = per_item[(per_item["sum"] == 0) & (per_item["count"] == len(models))].index
    lines = []
    for iid in allwrong:
        it = its[iid]
        picked = Counter(s[s.item_id == iid].chosen.dropna()).most_common(1)
        lines.append(
            f"- **{it.marker}** ({it.variety}): gold *{its[iid].choices['ABCD'.index(it.gold)]}*; "
            f"all models chose *{picked[0][0] if picked else '?'}*"
        )
    out.append(section(
        "Items every model gets wrong",
        f"{len(allwrong)} of {s.item_id.nunique()} items.\n\n" + ("\n".join(lines) or "_none_"),
    ))  # fmt: skip

    # 2. Words that are hard on the Belgian side only, across models.
    hard = s.groupby(["variety", "marker"]).correct.mean().reset_index().query("correct < 0.5")
    for v, label in (("be", "Belgian"), ("nl", "Netherlands")):
        rows = hard[hard.variety == v].sort_values("correct")
        body = "\n".join(
            f"- {r.marker} ({r.correct:.0%} of models correct)" for r in rows.itertuples()
        )
        out.append(section(f"{label} words most models miss ({len(rows)})", body or "_none_"))

    # 3. Does the gold's origin matter? (author/reviewer-checked vs bulk-kept)
    dec = curate.load_decisions()
    s["gold_source"] = [
        "checked" if dec.get((r.variety, r.marker), {}).get("decided_by") in ("author", "nl_reviewer")
        else "bulk"
        for r in s.itertuples()
    ]  # fmt: skip
    tab = s.pivot_table(
        index="gold_source", columns="variety", values="correct", aggfunc=["mean", "count"]
    )
    out.append(section("Accuracy by origin of the gold answer", tab.round(3).to_string()))

    # 4. Accuracy against how well humans know the word (prevalence bins).
    try:
        cand = pd.read_csv(lexicon.CANDIDATES, keep_default_na=False)
        p = {(r.variety, r.spelling): r.p_own for r in cand.itertuples()}
        s["p_own"] = [p.get((r.variety, r.marker)) for r in s.itertuples()]
        s["p_bin"] = pd.cut(s.p_own, [0.79, 0.85, 0.90, 0.95, 1.0])
        tab = s.pivot_table(
            index="p_bin", columns="variety", values="correct", aggfunc="mean", observed=True
        )
        out.append(section(
            "Accuracy by how well the word is known in its own country",
            tab.round(3).to_string() + "\n\n_Prevalence bins from the DCP norms (CC BY-NC); "
            "aggregate figures only._",
        ))  # fmt: skip
    except FileNotFoundError:
        out.append(section("Accuracy by prevalence", "_derived prevalence file not available_"))

    # 5. What do models pick when they are wrong?
    wrong = s[~s.correct.astype(bool)].copy()
    gloss_owner = {}
    for (v, w), r in dec.items():
        if r["decision"] == "keep" and r["gloss"]:
            gloss_owner.setdefault(r["gloss"], (v, w))
    wrong["distractor_variety"] = wrong.chosen.map(lambda g: (gloss_owner.get(g) or ("?", ""))[0])
    tab = wrong.pivot_table(
        index="variety", columns="distractor_variety", values="item_id", aggfunc="count"
    )
    out.append(section(
        "Which distractor is chosen when wrong",
        tab.fillna(0).astype(int).to_string()
        + "\n\n_Columns: the variety of the word whose meaning was chosen instead._",
    ))  # fmt: skip

    # 6. Per-model discordant pairs (one side right, the other wrong).
    lines = []
    for m in models:
        g = s[s.model == m]
        t = g.pivot_table(index="pair_id", columns="variety", values="correct")
        t = t.dropna()
        be_only = int(((t.be > 0.5) & (t.nl < 0.5)).sum())
        nl_only = int(((t.nl > 0.5) & (t.be < 0.5)).sum())
        lines.append(f"- {m}: BE right / NL wrong {be_only}, NL right / BE wrong {nl_only}")
    out.append(section("Discordant pairs per model", "\n".join(lines)))

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
