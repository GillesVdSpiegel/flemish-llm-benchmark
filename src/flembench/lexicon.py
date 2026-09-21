"""Lexicon candidates from the Dutch Crowdsourcing Project prevalence norms.

Source: Brysbaert, Keuleers, Mandera & Stevens (2019), "Recognition Times for 54 Thousand
Dutch Words: Data from the Dutch Crowdsourcing Project", Psychologica Belgica 59(1).
Data: https://osf.io/5fk8d/ — licensed CC BY-NC 4.0.

Licence boundary: prevalence values only ever land in data/derived/ (gitignored). What is
committed and published is the list of words and the author's decisions.

Prevalence is a probit score of the share of participants who said they knew the word; we
convert it back to a proportion. It measures word *recognition*, not meaning knowledge.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import norm

from flembench.paths import CURATION_DIR, DERIVED_DIR, EXTERNAL_DIR

SOURCE_URL = "https://osf.io/download/86245/"
SOURCE_PATH = EXTERNAL_DIR / "dcp_all_native.xlsx"
CANDIDATES = DERIVED_DIR / "lexicon_candidates.csv"
PAIRS_DERIVED = DERIVED_DIR / "lexicon_pairs.csv"
PAIRS_PUBLIC = CURATION_DIR / "lexicon_pairs.csv"
INFLECTION_SUFFIXES = ("en", "n", "s", "e", "je", "tje", "jes", "tjes", "ke", "kes")


def load_norms(path: Path = SOURCE_PATH) -> pd.DataFrame:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(SOURCE_URL, path)
    df = pd.read_excel(path).dropna(subset=["prevalence_BE", "prevalence_NL"])
    df["spelling"] = df["spelling"].astype(str)
    df["p_be"] = norm.cdf(df["prevalence_BE"])
    df["p_nl"] = norm.cdf(df["prevalence_NL"])
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
    """Mark forms that look like an inflection or diminutive of another candidate."""
    words = set(cands["spelling"])
    base_of = {}
    for w in words:
        for suf in INFLECTION_SUFFIXES:
            if w.endswith(suf) and w[: -len(suf)] in words:
                base_of[w] = w[: -len(suf)]
                break
    cands = cands.copy()
    cands["inflection_of"] = cands["spelling"].map(base_of)
    return cands


def build_candidates(
    df: pd.DataFrame, min_own: float = 0.80, min_gap: float = 0.30
) -> pd.DataFrame:
    cands = pd.concat([select(df, "be", min_own, min_gap), select(df, "nl", min_own, min_gap)])
    cols = ["variety", "spelling", "p_own", "p_other", "own_gap", "nobs"]
    return flag_inflections(cands[cols]).sort_values(
        ["variety", "own_gap"], ascending=[True, False]
    )


def match_pairs(
    be: pd.DataFrame, nl: pd.DataFrame, tol_own: float = 0.03, tol_gap: float = 0.05
) -> pd.DataFrame:
    """Optimal one-to-one matching on own-community prevalence and prevalence gap.
    Pairs outside either tolerance are never formed."""
    if be.empty or nl.empty:
        return pd.DataFrame(
            columns=["be_word", "be_p_own", "be_gap", "nl_word", "nl_p_own", "nl_gap"]
        )
    d_own = np.abs(be["p_own"].to_numpy()[:, None] - nl["p_own"].to_numpy()[None, :])
    d_gap = np.abs(be["own_gap"].to_numpy()[:, None] - nl["own_gap"].to_numpy()[None, :])
    cost = d_own / tol_own + d_gap / tol_gap
    cost = np.where((d_own > tol_own) | (d_gap > tol_gap), 1e6, cost)
    rows, cols = linear_sum_assignment(cost)
    keep = cost[rows, cols] < 1e6
    b = be.iloc[rows[keep]].reset_index(drop=True)
    n = nl.iloc[cols[keep]].reset_index(drop=True)
    out = pd.DataFrame(
        {
            "be_word": b["spelling"],
            "be_p_own": b["p_own"].round(3),
            "be_gap": b["own_gap"].round(3),
            "nl_word": n["spelling"],
            "nl_p_own": n["p_own"].round(3),
            "nl_gap": n["own_gap"].round(3),
        }
    )
    return out.sort_values("be_word").reset_index(drop=True)
