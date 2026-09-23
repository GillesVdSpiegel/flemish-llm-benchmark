"""Render the headline figure: the Flemish gap per model, as a diverging bar chart.

    uv run --with matplotlib python scripts/plot_gap.py

Computes from the response cache exactly as `flembench rescore` does - public AND held-out
pairs, first run, clean subset - so the figure always matches the reported headline. Set
FLEMBENCH_HELDOUT_DIR. Writes analysis/kloof.png.
Diverging form because the data's job is polarity around a zero baseline: blue = better on
Belgian Dutch, red = worse. Palette validated for colour-vision deficiency; the sign is also
carried by side of the baseline and by the signed labels, never by colour alone.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flembench import items as items_mod  # noqa: E402
from flembench import runner, stats  # noqa: E402
from flembench.registry import load_registry  # noqa: E402

OUT = ROOT / "analysis" / "kloof.png"
SURFACE, INK, INK_2, MUTED, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#c3c2b7"
BLUE, RED = "#2a78d6", "#e34948"
LABELS = {
    "chocollama-8b": "ChocoLlama-8B  (BE+NL data)",
    "geitje-7b-ultra": "GEITje-7B-ultra  (NL-data)",
    "gpt-5.6-terra": "GPT-5.6 Terra",
    "claude-sonnet-5": "Claude Sonnet 5",
    "eurollm-9b": "EuroLLM-9B",
    "gemini-3.8-flash": "Gemini 3.8 Flash",
    "gemma4-12b": "Gemma 4 12B",
}


def gaps() -> pd.DataFrame:
    res = items_mod.load_all()
    if res.errors:
        sys.exit(f"invalid items: {res.errors[:3]}")
    rows = runner.score_rows(runner.plan(res.items, load_registry().values()))
    s = pd.DataFrame(rows)
    s = s[(s.repeat == 0) & s.correct.notna() & (s.subcategory == "A1a-clean")]
    rows = []
    for model, g in s.groupby("model"):
        gp = stats.paired_gap(g)
        rows.append(
            {"model": model, "gap": gp.gap * 100, "lo": gp.ci_low * 100, "hi": gp.ci_high * 100}
        )
    return pd.DataFrame(rows).sort_values("gap")


def main() -> None:
    df = gaps()
    fig, ax = plt.subplots(figsize=(9, 5.4), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    y = range(len(df))
    colors = [BLUE if v > 0 else RED for v in df.gap]
    ax.barh(y, df.gap, height=0.52, color=colors, zorder=3)
    ax.errorbar(
        df.gap, y, xerr=[df.gap - df.lo, df.hi - df.gap], fmt="none",
        ecolor=MUTED, elinewidth=1.5, capsize=4, zorder=4,
    )  # fmt: skip

    for i, (gap, hi, lo) in enumerate(zip(df.gap, df.hi, df.lo, strict=True)):
        at = hi + 0.6 if gap > 0 else lo - 0.6
        ax.text(
            at, i, f"{gap:+.1f}", va="center", ha="left" if gap > 0 else "right",
            color=INK, fontsize=11, fontweight="semibold",
        )  # fmt: skip

    ax.set_yticks(list(y), [LABELS.get(m, m) for m in df.model], fontsize=11, color=INK_2)
    ax.axvline(0, color=AXIS, linewidth=1.2, zorder=2)
    ax.set_xlim(-15, 18)
    ax.set_xticks(range(-15, 20, 5))
    ax.set_xticklabels([f"{v:+d}" if v else "0" for v in range(-15, 20, 5)])
    ax.tick_params(axis="x", colors=MUTED, labelsize=9.5)
    ax.grid(axis="x", color="#e1e0d9", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    fig.text(
        0.012, 0.945, "Kent AI Vlaams? Het verschil zit in de trainingsdata",
        color=INK, fontsize=15.5, fontweight="bold", va="top",
    )  # fmt: skip
    fig.text(
        0.012, 0.885,
        "Woordenschatscore Belgisch-Nederlands min Nederlands-Nederlands, in procentpunten\n"
        "373 woordparen, gekoppeld op hoe goed mensen het woord in eigen land kennen",
        color=INK_2, fontsize=9.5, va="top", linespacing=1.5,
    )  # fmt: skip
    ax.text(
        -14.6, len(df) - 0.3, "◀ slechter op Belgisch-Nederlands", color=RED, fontsize=10,
        fontweight="semibold", va="center",
    )  # fmt: skip
    ax.text(
        17.6, len(df) - 0.3, "beter op Belgisch-Nederlands ▶", color=BLUE, fontsize=10,
        fontweight="semibold", va="center", ha="right",
    )  # fmt: skip
    fig.text(
        0.012,
        0.02,
        "Streepjes = 95 %-betrouwbaarheidsinterval · 7 modellen, september 2026 · "
        "data: huggingface.co/datasets/Goomey/flembench",
        color=MUTED,
        fontsize=8.5,
    )
    fig.subplots_adjust(left=0.30, right=0.97, top=0.76, bottom=0.13)
    fig.savefig(OUT, facecolor=SURFACE)
    print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size // 1024} kB)")


if __name__ == "__main__":
    main()
