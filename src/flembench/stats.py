"""Paired gap estimates. Gap = mean over pairs of (score_BE - score_NL); negative means
the model does worse on Belgian Dutch. CIs bootstrap over *pairs*, never over items."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import binomtest


@dataclass(frozen=True)
class Gap:
    n_pairs: int
    acc_be: float
    acc_nl: float
    gap: float
    ci_low: float
    ci_high: float
    be_only: int  # discordant: BE right, NL wrong
    nl_only: int  # discordant: NL right, BE wrong
    p_mcnemar: float


def pair_table(scores: pd.DataFrame) -> pd.DataFrame:
    """One row per pair: BE and NL correctness (averaged over repeats)."""
    s = scores[scores["pair_id"].notna() & scores["correct"].notna()].copy()
    s["correct"] = s["correct"].astype(float)
    t = s.groupby(["pair_id", "variety"])["correct"].mean().unstack("variety")
    return t.dropna(subset=["be", "nl"])


def paired_gap(scores: pd.DataFrame, n_boot: int = 10_000, seed: int = 0) -> Gap:
    t = pair_table(scores)
    be, nl = t["be"].to_numpy(), t["nl"].to_numpy()
    n = len(t)
    if n == 0:
        raise ValueError("no complete pairs")
    diff = be - nl
    rng = np.random.default_rng(seed)
    boots = diff[rng.integers(0, n, size=(n_boot, n))].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    be_only = int(((be >= 0.5) & (nl < 0.5)).sum())
    nl_only = int(((nl >= 0.5) & (be < 0.5)).sum())
    k = be_only + nl_only
    p = binomtest(be_only, k, 0.5).pvalue if k else 1.0
    return Gap(
        n,
        float(be.mean()),
        float(nl.mean()),
        float(diff.mean()),
        float(lo),
        float(hi),
        be_only,
        nl_only,
        float(p),
    )


def ci_halfwidth(n_pairs: int, discordant: float) -> float:
    """Normal-approximation 95% CI half-width of a paired binary gap at zero effect."""
    return 1.96 * float(np.sqrt(discordant / n_pairs))
