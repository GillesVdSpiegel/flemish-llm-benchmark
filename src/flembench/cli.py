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
        register = gloss = note = ""
        if key == "k":
            console.print(
                "\n  register: [bold]s[/] standard  [bold]t[/] tussentaal  [bold]d[/] dialect"
            )
            rk = readchar.readkey().lower()
            register = curate.REGISTERS.get(rk, "")
            gloss = console.input("  meaning (gloss, Enter to skip): ").strip()
        elif key == "u":
            note = console.input("  note (optional): ").strip()
        s.decide(key, register=register, gloss=gloss, note=note)
        curate.save_decisions(s.decided)

    console.print(f"\nsaved to {curate.DECISIONS_FILE.relative_to(ITEMS_DIR.parent)}")
    console.print_json(data=s.counts())


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


@lex.command("prefilter-report")
def lex_prefilter_report() -> None:
    """Prefilter vs author agreement on the blind audit sample."""
    from flembench import curate, prefilter

    console.print_json(data=prefilter.report(curate.load_decisions()))


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
        index=["model", "category"], columns="variety", values="correct", aggfunc="mean"
    )
    console.print(acc.round(3).to_string())
    parse_fail = df.groupby("model")["parse"].apply(lambda s: (s == "none").mean())
    console.print("\nunparseable share per model:\n" + parse_fail.round(3).to_string())
    for model, g in df[df["pair_id"].notna()].groupby("model"):
        for track, cats in {"language (A)": {"A1", "A2"}, "context (B)": {"B1"}}.items():
            sub = g[g["category"].isin(cats)]
            if sub.empty:
                continue
            gp = stats.paired_gap(sub)
            console.print(
                f"{model:>18} {track:<13} gap {gp.gap:+.3f} "
                f"[{gp.ci_low:+.3f}, {gp.ci_high:+.3f}] n={gp.n_pairs} p={gp.p_mcnemar:.3f}"
            )
    console.print(f"\nwrote {len(public)} public rows to runs/scores.csv")


if __name__ == "__main__":
    app()
