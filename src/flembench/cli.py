from __future__ import annotations

import json
import sys

import pandas as pd
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from flembench import items as items_mod
from flembench import lexicon
from flembench.paths import COMPILED_ITEMS, ITEMS_DIR, RUNS_DIR, SCHEMA_FILE
from flembench.registry import load_registry
from flembench.schema import Item

app = typer.Typer(no_args_is_help=True, add_completion=False)
lex = typer.Typer(no_args_is_help=True, help="Lexicon (A1) candidate pipeline.")
app.add_typer(lex, name="lexicon")
console = Console()


@app.callback()
def _main() -> None:
    load_dotenv()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


# ------------------------------------------------------------------ items


@app.command()
def schema() -> None:
    """Write the JSON Schema generated from the pydantic item model."""
    SCHEMA_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_FILE.write_text(
        json.dumps(Item.model_json_schema(), indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    console.print(f"wrote {SCHEMA_FILE.relative_to(ITEMS_DIR.parent)}")


def _load_or_exit() -> list[Item]:
    res = items_mod.load_all()
    for e in res.errors:
        console.print(f"[red]✗[/] {e}")
    if res.errors:
        console.print(f"[red]{len(res.errors)} error(s)[/]")
        raise typer.Exit(1)
    return res.items


@app.command()
def validate() -> None:
    """Validate all authored items (public, plus held-out if FLEMBENCH_HELDOUT_DIR is set)."""
    its = _load_or_exit()
    console.print(f"[green]✓[/] {len(its)} items valid")
    console.print_json(data=items_mod.summary(its))


@app.command(name="compile")
def compile_() -> None:
    """Validate and write public items to data/items.jsonl."""
    its = [i for i in _load_or_exit() if i.split == "public"]
    items_mod.write_jsonl(its)
    console.print(f"[green]✓[/] wrote {len(its)} public items to {COMPILED_ITEMS.name}")


# ------------------------------------------------------------------ lexicon


@lex.command("candidates")
def lex_candidates(min_own: float = 0.80, min_gap: float = 0.30) -> None:
    """Extract BE/NL-specific candidates from the prevalence norms (downloads on first use)."""
    df = lexicon.load_norms()
    c = lexicon.build_candidates(df, min_own, min_gap)
    lexicon.CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    c.round(3).to_csv(lexicon.CANDIDATES, index=False)
    counts = c.groupby("variety").size().to_dict()
    console.print(
        f"{len(df)} words in norms; candidates: {counts} → {lexicon.CANDIDATES.name} (gitignored)"
    )


@lex.command("curate")
def lex_curate(seed: int = 0) -> None:
    """Keyboard curation of candidates. Decisions are saved after every key press."""
    import readchar

    from flembench import curate

    if not lexicon.CANDIDATES.exists():
        console.print("[red]run `flembench lexicon candidates` first[/]")
        raise typer.Exit(1)
    df = pd.read_csv(lexicon.CANDIDATES, keep_default_na=False)
    cands = [
        curate.Candidate(r.variety, r.spelling, r.inflection_of or None) for r in df.itertuples()
    ]
    from rich.markup import escape

    from flembench import glosses as gl

    drafts = gl.load()
    by_key = {(c.variety, c.word): c for c in cands}
    s = curate.Session.create(cands, curate.load_decisions(), seed=seed)
    help_line = "  ".join(f"[bold]{k}[/] {v[0]}" for k, v in curate.DECISIONS.items())
    help_line += "  [bold]space[/] skip  [bold]z[/] undo  [bold]q[/] quit"

    while (c := s.current) is not None:
        console.clear()
        done, total = len(s.decided), len(cands)
        kept = {
            v: sum(1 for r in s.decided.values() if r["variety"] == v and r["decision"] == "keep")
            for v in ("be", "nl")
        }
        console.print(f"[dim]{done}/{total} decided · kept BE {kept['be']} · NL {kept['nl']}[/]\n")
        label = (
            "[cyan]Belgisch-Nederlands[/]"
            if c.variety == "be"
            else "[magenta]Nederlands-Nederlands[/]"
        )
        console.print(f"  {label}\n\n     [bold white]{c.word}[/]\n")
        if c.inflection_of:
            console.print(f"  [yellow]possible inflection of '{c.inflection_of}'[/]\n")
        row = drafts.get((c.variety, c.word))
        if row:
            conf = row["claude_confidence"]
            claude = escape(row["claude_gloss"]) or "[dim]?[/]"
            console.print(f"  [dim]Claude[/]  {claude}  [dim]({conf})[/]")
            if row.get("gemini_gloss"):
                console.print(f"  [dim]Gemini[/]  {escape(row['gemini_gloss'])}")
            if row.get("agreement") == "differ":
                console.print("  [yellow]drafts differ: check the meaning[/]")
            console.print()
        console.print(help_line)
        key = readchar.readkey().lower()
        if key == "q":
            break
        if key == " ":
            s.skip()
            continue
        if key == "z":
            s.undo(by_key)
            curate.save_decisions(s.decided)
            continue
        if key not in curate.DECISIONS:
            continue
        register = gloss = note = source = ""
        if key == "k":
            console.print(
                "\n  register: [bold]s[/] standard  [bold]t[/] tussentaal  [bold]d[/] dialect"
            )
            rk = readchar.readkey().lower()
            register = curate.REGISTERS.get(rk, "")
            draft, draft_src = gl.draft_for(row)
            hint = f"Enter = accept '{escape(draft)}'" if draft else "Enter to skip"
            typed = console.input(f"  meaning ({hint}, or type your own): ").strip()
            if typed:
                gloss, source = typed, "author"
            elif draft:
                gloss, source = draft, f"{draft_src} (accepted by author)"
        elif key == "u":
            note = console.input("  note (optional): ").strip()
        s.decide(key, register=register, gloss=gloss, note=note, gloss_source=source)
        curate.save_decisions(s.decided)

    console.print(f"\nsaved to {curate.DECISIONS_FILE.relative_to(ITEMS_DIR.parent)}")
    console.print_json(data=s.counts())


@lex.command("bulk-keep")
def lex_bulk_keep() -> None:
    """Keep all remaining undecided candidates with their draft gloss (marked unverified)."""
    from collections import Counter

    from flembench import curate
    from flembench import glosses as gl

    df = pd.read_csv(lexicon.CANDIDATES, keep_default_na=False)
    cands = [curate.Candidate(r.variety, r.spelling) for r in df.itertuples()]
    decided, added = curate.bulk_keep(curate.load_decisions(), cands, gl.load())
    curate.save_decisions(decided)
    by = Counter((r["decided_by"], r["decision"]) for r in decided.values())
    console.print(f"bulk-kept {added} words")
    console.print_json(data={f"{a}:{b}": n for (a, b), n in sorted(by.items())})


@lex.command("review-glosses")
def lex_review_glosses() -> None:
    """Resolve words where the Claude and Gemini glosses disagree. Saved after every word."""
    import readchar
    from rich.markup import escape

    from flembench import curate
    from flembench import glosses as gl

    drafts = gl.load()
    decided = curate.load_decisions()
    queue = curate.gloss_review_queue(decided, drafts)
    total = len(queue)
    for n, key in enumerate(queue, start=1):
        d, cur = drafts[key], decided[key]
        console.clear()
        label = (
            "[cyan]Belgisch-Nederlands[/]"
            if key[0] == "be"
            else "[magenta]Nederlands-Nederlands[/]"
        )
        console.print(f"[dim]{n}/{total}[/]\n\n  {label}\n\n     [bold white]{key[1]}[/]\n")
        console.print(f"  [bold]1[/] Claude  {escape(d['claude_gloss']) or '[dim]?[/]'}")
        console.print(f"  [bold]2[/] Gemini  {escape(d['gemini_gloss']) or '[dim]?[/]'}")
        console.print(
            "\n  [bold]e[/] type your own   [bold]u[/] I don't know it (goes to the NL reviewer)"
            "   [bold]space[/] skip   [bold]q[/] quit"
        )
        while True:
            k = readchar.readkey().lower()
            if k in {"1", "2", "e", "u", " ", "q"}:
                break
        if k == "q":
            break
        if k == " ":
            continue
        if k == "1":
            decided = curate.set_gloss(
                decided, key, d["claude_gloss"], "claude-opus-5 (chosen by author)"
            )
        elif k == "2":
            src = d.get("gemini_model") or "gemini"
            decided = curate.set_gloss(decided, key, d["gemini_gloss"], f"{src} (chosen by author)")
        elif k == "e":
            typed = console.input("\n  meaning: ").strip()
            if not typed:
                continue
            decided = curate.set_gloss(decided, key, typed, "author")
        elif k == "u":
            decided = {**decided, key: {**cur, "decision": "needs_other_variety_speaker",
                                        "decided_by": "author"}}  # fmt: skip
        curate.save_decisions(decided)
    left = len(curate.gloss_review_queue(decided, drafts))
    console.print(f"\nsaved. {left} flagged words still open")


@lex.command("pair")
def lex_pair(tol_own: float = 0.03, tol_gap: float = 0.05) -> None:
    """Match kept BE and NL words into prevalence-matched pairs."""
    from flembench import curate

    c = pd.read_csv(lexicon.CANDIDATES, keep_default_na=False)
    kept = {k for k, r in curate.load_decisions().items() if r["decision"] == "keep"}
    c = c[[(v, w) in kept for v, w in zip(c.variety, c.spelling, strict=True)]]
    pairs = lexicon.match_pairs(c[c.variety == "be"], c[c.variety == "nl"], tol_own, tol_gap)
    pairs.to_csv(lexicon.PAIRS_DERIVED, index=False)
    lexicon.PAIRS_PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    pairs[["be_word", "nl_word"]].to_csv(lexicon.PAIRS_PUBLIC, index=False, lineterminator="\n")
    n_be, n_nl = (c.variety == "be").sum(), (c.variety == "nl").sum()
    console.print(
        f"kept BE {n_be} / NL {n_nl} → {len(pairs)} matched pairs "
        f"(tolerance own ±{tol_own}, gap ±{tol_gap})"
    )


@lex.command("prefilter-export")
def lex_prefilter_export(batch_size: int = 200) -> None:
    """Write the prefilter prompt, id map and batches for pasting into chat LLMs."""
    from flembench import prefilter

    c = pd.read_csv(lexicon.CANDIDATES, keep_default_na=False)
    paths = prefilter.export(list(zip(c.variety, c.spelling, strict=True)), batch_size)
    rel = prefilter.DIR.relative_to(ITEMS_DIR.parent).as_posix()
    console.print(f"{len(c)} words in {len(paths)} batches → {rel}/batches/")
    console.print(f"prompt: {rel}/PROMPT.md · save outputs as {rel}/results/<model>__NN.txt")


@lex.command("prefilter-import")
def lex_prefilter_import(seed: int = 0) -> None:
    """Apply unanimous form-based verdicts (>= 2 models) and hold back a blind audit sample."""
    from flembench import curate, prefilter

    decided, stats = prefilter.apply(curate.load_decisions(), seed=seed)
    curate.save_decisions(decided)
    for p in stats.pop("problems"):
        console.print(f"[yellow]![/] {p}")
    console.print_json(data=stats)


def _word_ids() -> dict[str, tuple[str, str]]:
    from flembench import prefilter

    return {i: (w.variety, w.word) for i, w in prefilter.load_words().items()}


@lex.command("gloss-export")
def lex_gloss_export(batch_size: int = 200) -> None:
    """Write the gloss prompt and batches for a second, independent model (e.g. Gemini)."""
    from flembench import glosses as gl

    ids = _word_ids()
    paths = gl.export([(i, v, w) for i, (v, w) in ids.items()], batch_size)
    rel = gl.PROMPT_DIR.relative_to(ITEMS_DIR.parent).as_posix()
    console.print(f"{len(ids)} words in {len(paths)} batches → {rel}/batches/")
    console.print(f"prompt: {rel}/PROMPT.md · save outputs as {rel}/results/<model>__NN.txt")


@lex.command("gloss-import")
def lex_gloss_import() -> None:
    """Read the second model's glosses into data/curation/glosses.csv."""
    from flembench import glosses as gl

    merged, stats = gl.import_results(gl.load(), _word_ids())
    gl.save(merged)
    for p in stats.pop("problems"):
        console.print(f"[yellow]![/] {p}")
    console.print_json(data=stats)


@lex.command("b1-pool")
def lex_b1_pool() -> None:
    """List words routed to the B1 (institutional) pool, by you or by the prefilter."""
    from flembench import curate

    rows = [r for r in curate.load_decisions().values() if r["decision"] == "move_to_b1"]
    t = Table("variety", "word", "decided by", "note")
    for r in sorted(rows, key=lambda r: (r["variety"], r["word"])):
        t.add_row(r["variety"], r["word"], r.get("decided_by", ""), r.get("note", ""))
    console.print(t)
    console.print(f"{len(rows)} words in the B1 pool")


@lex.command("reopen")
def lex_reopen(
    word: str,
    variety: str = typer.Option(None, help="be or nl; needed only if the word is in both lists"),
    note: str = "",
) -> None:
    """Put a word back in your curation queue (e.g. an eponym like 'pfeiffer' routed to B1)."""
    from flembench import curate

    c = pd.read_csv(lexicon.CANDIDATES, keep_default_na=False)
    varieties = sorted(set(c[c.spelling == word].variety))
    if variety:
        varieties = [v for v in varieties if v == variety]
    if len(varieties) != 1:
        console.print(f"[red]'{word}' matches varieties {varieties}; use --variety be|nl[/]")
        raise typer.Exit(1)
    decided = curate.reopen(curate.load_decisions(), varieties[0], word, note)
    curate.save_decisions(decided)
    console.print(f"reopened {varieties[0]}:{word}: it is back in `lexicon curate`")


@lex.command("prefilter-report")
def lex_prefilter_report() -> None:
    """Prefilter vs author agreement on the blind audit sample."""
    from flembench import curate, prefilter

    console.print_json(data=prefilter.report(curate.load_decisions()))


@app.command("generate-a1")
def generate_a1(seed: int = 0) -> None:
    """(Re)generate the automatic lexicon track from lexicon_pairs.csv and the decisions."""
    import os
    import shutil
    from collections import Counter
    from pathlib import Path

    from flembench import curate, generate

    heldout_root = os.environ.get(items_mod.HELDOUT_ENV)
    if not heldout_root:
        console.print(f"[red]set {items_mod.HELDOUT_ENV} to the private held-out repo first[/]")
        raise typer.Exit(1)
    public_dir = ITEMS_DIR / "A1" / "auto"
    heldout_dir = Path(heldout_root) / "items" / "A1" / "auto"
    for d in (public_dir, heldout_dir):
        shutil.rmtree(d, ignore_errors=True)
    docs = generate.build(curate.load_decisions(), generate.load_pairs(), seed=seed)
    counts = generate.write(docs, public_dir, heldout_dir)
    sub = Counter((d["split"], d["subcategory"]) for d in docs)
    console.print(f"pairs written: {counts}")
    console.print_json(data={f"{a}:{b}": n for (a, b), n in sorted(sub.items())})


# ------------------------------------------------------------------ runs


def _select(models: str, category: str | None) -> tuple[list, list[Item]]:
    reg = load_registry()
    keys = [m.strip() for m in models.split(",")]
    missing = [k for k in keys if k not in reg]
    if missing:
        console.print(f"[red]unknown model(s): {missing}. Known: {list(reg)}[/]")
        raise typer.Exit(1)
    its = _load_or_exit()
    if category:
        cats = set(category.split(","))
        its = [i for i in its if i.category in cats]
    return [reg[k] for k in keys], its


@app.command()
def estimate(models: str, category: str | None = None, repeats: int = 1) -> None:
    """Estimate the cost of a run without calling any model."""
    from flembench import runner

    specs, its = _select(models, category)
    _print_estimate(runner.estimate(runner.plan(its, specs, repeats)))


def _print_estimate(ests) -> float:
    t = Table("model", "new calls", "cached", "expected $", "worst case $")
    for e in ests:
        t.add_row(
            e.model, str(e.calls), str(e.cached), f"{e.expected_usd:.4f}", f"{e.worst_case_usd:.4f}"
        )
    console.print(t)
    total = sum(e.expected_usd for e in ests)
    console.print(
        f"expected total ≈ ${total:.4f} (×2 safety factor included); "
        f"worst case ${sum(e.worst_case_usd for e in ests):.4f} if every call hit max tokens"
    )
    return total


@app.command()
def run(
    models: str,
    budget: float = typer.Option(..., help="Hard stop in USD for this invocation."),
    category: str | None = None,
    repeats: int = 1,
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt."),
) -> None:
    """Query models for all uncached items, after showing the cost estimate."""
    from flembench import runner

    specs, its = _select(models, category)
    jobs = runner.plan(its, specs, repeats)
    _print_estimate(runner.estimate(jobs))
    if not yes and not typer.confirm("run?"):
        raise typer.Exit(0)
    done = 0

    def progress(job, entry):
        nonlocal done
        done += 1
        console.print(
            f"[dim]{done}[/] {job.model.key} {job.item.id} r{job.repeat} "
            f"→ {entry['completion']['text'][:40]!r} ${entry['cost_usd']:.5f}"
        )

    try:
        spent = runner.execute(jobs, budget, progress=progress)
    except runner.BudgetExceeded as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(2) from e
    console.print(f"[green]done[/], spent ${spent:.4f}")


@app.command()
def rescore(repeats: int = 3) -> None:
    """Re-score every cached response for every registered model. Never calls a provider."""
    from flembench import runner, stats

    reg = load_registry()
    its = _load_or_exit()
    rows = runner.score_rows(runner.plan(its, reg.values(), repeats))
    public = [r for r in rows if r["split"] == "public"]
    runner.write_scores(public, RUNS_DIR / "scores.csv")
    if not rows:
        console.print("no cached responses yet")
        return
    df = pd.DataFrame(rows)
    df = df[df["correct"].notna()]
    acc = df.pivot_table(
        index=["model", "subcategory"], columns="variety", values="correct", aggfunc="mean"
    )
    console.print(acc.round(3).to_string())
    parse_fail = df.groupby("model")["parse"].apply(lambda s: (s == "none").mean())
    console.print("\nunparseable share per model:\n" + parse_fail.round(3).to_string())
    groups = {
        "A1 clean (headline)": lambda s: s["subcategory"] == "A1a-clean",
        "A1 look-alike": lambda s: s["subcategory"] == "A1a-overlap",
        "A1 all": lambda s: s["category"] == "A1",
        "context (B)": lambda s: s["category"] == "B1",
    }
    t = Table("model", "track", "acc BE", "acc NL", "gap BE-NL", "95% CI", "pairs", "p")
    for model, g in df[df["pair_id"].notna()].groupby("model"):
        for track, sel in groups.items():
            sub = g[sel(g)]
            if sub.empty:
                continue
            gp = stats.paired_gap(sub)
            t.add_row(
                model, track, f"{gp.acc_be:.3f}", f"{gp.acc_nl:.3f}", f"{gp.gap:+.3f}",
                f"[{gp.ci_low:+.3f}, {gp.ci_high:+.3f}]", str(gp.n_pairs), f"{gp.p_mcnemar:.3f}",
            )  # fmt: skip
    console.print(t)
    console.print(f"\nwrote {len(public)} public rows to runs/scores.csv")


if __name__ == "__main__":
    app()
