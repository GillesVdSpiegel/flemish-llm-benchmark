"""Extract Belgian- and Netherlands-specific word candidates from the Dutch
Crowdsourcing Project prevalence norms and propose prevalence-matched pairs.

Source: Brysbaert, Keuleers, Mandera & Stevens (2019), "Recognition Times for
54 Thousand Dutch Words: Data from the Dutch Crowdsourcing Project",
Psychologica Belgica 59(1). Data: https://osf.io/5fk8d/ (CC BY-NC 4.0).

Licence boundary: prevalence values are CC BY-NC. Outputs of this script are
written to data/derived/ (gitignored) and must never be committed or published.
Only the words and the author's curation decisions enter the dataset.

Prevalence in the source is a probit score of the proportion of participants
who indicated knowing the word; we convert it back to a proportion.
Note that it measures word *recognition*, not knowledge of the correct meaning.
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://osf.io/download/86245/"
SOURCE_PATH = ROOT / "data" / "external" / "dcp_all_native.xlsx"
OUT_DIR = ROOT / "data" / "derived"

INFLECTION_SUFFIXES = ("en", "n", "s", "e", "je", "tje", "jes", "tjes", "ke", "kes")


def load_norms(path: Path = SOURCE_PATH) -> pd.DataFrame:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(SOURCE_URL, path)
    df = pd.read_excel(path).dropna(subset=["prevalence_BE", "prevalence_NL"])
    df["spelling"] = df["spelling"].astype(str)
    df["p_be"] = norm.cdf(df["prevalence_BE"])
    df["p_nl"] = norm.cdf(df["prevalence_NL"])
    df["gap"] = df["p_be"] - df["p_nl"]
    return df


def select(df: pd.DataFrame, variety: str, min_own: float, min_gap: float) -> pd.DataFrame:
    own, other = ("p_be", "p_nl") if variety == "be" else ("p_nl", "p_be")
    out = df[(df[own] >= min_own) & (df[own] - df[other] >= min_gap)].copy()
    out["variety"] = variety
    out["p_own"] = out[own]
    out["p_other"] = out[other]
    out["own_gap"] = out[own] - out[other]
    return out


def flag_inflections(cands: pd.DataFrame) -> pd.DataFrame:
    """Mark forms that look like an inflection/diminutive of another candidate."""
    words = set(cands["spelling"])
    base_of = {}
    for w in words:
        for suf in INFLECTION_SUFFIXES:
            if w.endswith(suf) and w[: -len(suf)] in words:
                base_of[w] = w[: -len(suf)]
                break
    cands["inflection_of"] = cands["spelling"].map(base_of)
    return cands


def match_pairs(be: pd.DataFrame, nl: pd.DataFrame, tol_own: float, tol_gap: float) -> pd.DataFrame:
    """Optimal one-to-one matching on own-community prevalence and prevalence gap."""
    cost = (
        np.abs(be["p_own"].to_numpy()[:, None] - nl["p_own"].to_numpy()[None, :]) / tol_own
        + np.abs(be["own_gap"].to_numpy()[:, None] - nl["own_gap"].to_numpy()[None, :]) / tol_gap
    )
    invalid = (
        np.abs(be["p_own"].to_numpy()[:, None] - nl["p_own"].to_numpy()[None, :]) > tol_own
    ) | (np.abs(be["own_gap"].to_numpy()[:, None] - nl["own_gap"].to_numpy()[None, :]) > tol_gap)
    cost = np.where(invalid, 1e6, cost)
    rows, cols = linear_sum_assignment(cost)
    keep = cost[rows, cols] < 1e6
    b, n = be.iloc[rows[keep]].reset_index(drop=True), nl.iloc[cols[keep]].reset_index(drop=True)
    return pd.DataFrame(
        {
            "be_word": b["spelling"],
            "be_p_own": b["p_own"].round(3),
            "be_gap": b["own_gap"].round(3),
            "nl_word": n["spelling"],
            "nl_p_own": n["p_own"].round(3),
            "nl_gap": n["own_gap"].round(3),
        }
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--min-own", type=float, default=0.80)
    ap.add_argument("--min-gap", type=float, default=0.30)
    ap.add_argument("--tol-own", type=float, default=0.03)
    ap.add_argument("--tol-gap", type=float, default=0.05)
    args = ap.parse_args()

    df = load_norms()
    cands = pd.concat(
        [select(df, "be", args.min_own, args.min_gap), select(df, "nl", args.min_own, args.min_gap)]
    )
    cands = flag_inflections(cands)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cols = ["variety", "spelling", "p_own", "p_other", "own_gap", "inflection_of", "nobs"]
    cands.sort_values(["variety", "own_gap"], ascending=[True, False])[cols].round(3).to_csv(
        OUT_DIR / "lexicon_candidates.csv", index=False
    )

    base = cands[cands["inflection_of"].isna()]
    be, nl = base[base.variety == "be"], base[base.variety == "nl"]
    pairs = match_pairs(be, nl, args.tol_own, args.tol_gap)
    pairs.to_csv(OUT_DIR / "lexicon_pairs_uncurated.csv", index=False)

    print(f"norms: {len(df)} words; thresholds own>={args.min_own} gap>={args.min_gap}")
    print(f"candidates: be={len(cands[cands.variety == 'be'])} nl={len(cands[cands.variety == 'nl'])}")
    print(f"after dropping inflections: be={len(be)} nl={len(nl)}")
    print(f"matched pairs (tol own={args.tol_own}, gap={args.tol_gap}): {len(pairs)}")
    print(f"written to {OUT_DIR.relative_to(ROOT)}/ (gitignored, CC BY-NC derived)")


if __name__ == "__main__":
    main()
