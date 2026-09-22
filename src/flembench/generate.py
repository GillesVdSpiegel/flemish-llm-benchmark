"""Generate the automatic lexicon track (A1a) from matched pairs and curated glosses.

Every word of a matched BE/NL pair becomes one multiple-choice item from a fixed template:

    Wat betekent het woord "zwalpen" zoals het in België gebruikt wordt?

The correct option is the word's curated gloss. The three distractors are glosses of other
candidate words (both varieties pooled, so BE and NL items draw from the same answer space),
chosen with a seed per pair and filtered so that no distractor shares a content word with the
gold gloss or resembles the target word, and so that option lengths are comparable.

Form overlap. Some glosses resemble the word itself (bakkerin -> bakkersvrouw); a model can then
pick the answer by string similarity. Giveaways that are pure formatting are removed (the word in
brackets, an idiom before a colon). Pairs where either gloss still resembles its word get
subcategory A1a-overlap; all others A1a-clean. The headline gap uses A1a-clean.
"""

from __future__ import annotations

import csv
import hashlib
import random
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from flembench.paths import CURATION_DIR

PAIRS_FILE = CURATION_DIR / "lexicon_pairs.csv"
COUNTRY = {"be": "België", "nl": "Nederland"}
TEMPLATE = 'Wat betekent het woord "{word}" zoals het in {country} gebruikt wordt?'
HELDOUT_SHARE = 0.20
N_DISTRACTORS = 3
_STOP = {
    "een", "het", "de", "van", "voor", "met", "die", "dat", "als", "ook", "bij", "aan", "zich",
    "iets", "iemand", "wie", "wat", "zijn", "door", "niet", "wordt", "worden", "heel", "zeer",
}  # fmt: skip


def _seed(key: str) -> int:
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "big")


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zà-ÿ]+", text.lower()) if len(t) >= 4 and t not in _STOP}


def clean_gloss(gloss: str, word: str) -> str:
    """Remove formatting giveaways: an idiom before the last colon, brackets naming the word."""
    g = gloss.strip()
    if ":" in g:
        tail = g.rsplit(":", 1)[1].strip()
        if tail:
            g = tail
    g = re.sub(
        r"\s*\([^)]*\)", lambda m: "" if word.lower() in m.group(0).lower() else m.group(0), g
    )
    return g.strip(" ;,") or gloss.strip()


def resembles(word: str, gloss: str) -> bool:
    """True if a gloss token shares a 5-letter stem with the word (or contains it)."""
    w = word.lower()
    stem = w[:5]
    for t in re.findall(r"[a-zà-ÿ]+", gloss.lower()):
        if w in t or (len(t) >= 5 and len(w) >= 5 and (t.startswith(stem) or w.startswith(t[:5]))):
            return True
    return False


@dataclass
class Entry:
    variety: str
    word: str
    gloss: str
    source: str
    decided_by: str
    register: str


def pick_distractors(
    target: Entry, pool: list[Entry], exclude: set[tuple[str, str]], seed: int
) -> list[str]:
    """Three glosses unrelated to the gold, not resembling the target word, similar length."""
    gold_tok = _tokens(target.gloss)
    glen = len(target.gloss)
    rng = random.Random(seed)
    order = pool[:]
    rng.shuffle(order)
    chosen: list[str] = []
    for tolerance in (0.5, 1.0, None):  # relax the length constraint only if needed
        for e in order:
            if len(chosen) == N_DISTRACTORS:
                return chosen
            g = e.gloss
            if (e.variety, e.word) in exclude or g in chosen or g == target.gloss:
                continue
            if _tokens(g) & gold_tok or any(_tokens(g) & _tokens(c) for c in chosen):
                continue
            if resembles(target.word, g):
                continue
            if tolerance is not None and not (
                glen * (1 - tolerance) <= len(g) <= glen * (1 + tolerance) + 8
            ):
                continue
            chosen.append(g)
    if len(chosen) < N_DISTRACTORS:
        raise ValueError(f"not enough distractors for {target.word}")
    return chosen


def build(decisions: dict[tuple[str, str], dict], pairs: list[dict], seed: int = 0) -> list[dict]:
    """Return one YAML-ready document per pair, with split assigned (seeded)."""
    kept = {
        k: Entry(k[0], k[1], clean_gloss(r["gloss"], k[1]), r.get("gloss_source", ""),
                 r.get("decided_by", ""), r.get("register") or "unspecified")
        for k, r in decisions.items()
        if r["decision"] == "keep" and r["gloss"]
    }  # fmt: skip
    pool = list(kept.values())
    ordered = sorted(pairs, key=lambda p: (p["be_word"], p["nl_word"]))
    rng = random.Random(seed)
    heldout = set(rng.sample(range(len(ordered)), round(len(ordered) * HELDOUT_SHARE)))
    docs = []
    for n, p in enumerate(ordered, start=1):
        pid = f"a1a-{n:04d}"
        be, nl = kept[("be", p["be_word"])], kept[("nl", p["nl_word"])]
        overlap = resembles(be.word, be.gloss) or resembles(nl.word, nl.gloss)
        exclude = {("be", be.word), ("nl", nl.word)}
        doc = {
            "pair_id": pid,
            "category": "A1",
            "subcategory": "A1a-overlap" if overlap else "A1a-clean",
            "format": "mc",
            "match_basis": "dcp_prevalence",
            "lexical_source": "DCP prevalence norms (Brysbaert et al. 2019)",
            "author": "flembench-generator",
            "provenance": "template_generated",
            "split": "heldout" if n - 1 in heldout else "public",
        }
        for v, e in (("be", be), ("nl", nl)):
            distractors = pick_distractors(e, pool, exclude, _seed(f"{pid}-{v}"))
            doc[v] = {
                "marker": e.word,
                "register": e.register,
                "prompt": TEMPLATE.format(word=e.word, country=COUNTRY[v]),
                "choices": [e.gloss, *distractors],
                "drafted_by": e.source.split(" ")[0] or None,
                "reviewed_by": [e.decided_by] if e.decided_by in {"author", "nl_reviewer"} else [],
                "notes": f"gold gloss: {e.source or 'unknown'}; decided_by: {e.decided_by}",
            }
        docs.append(doc)
    return docs


def load_pairs(path: Path = PAIRS_FILE) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write(docs: list[dict], public_dir: Path, heldout_dir: Path | None) -> dict[str, int]:
    """One YAML file per pair. Held-out pairs go only to the private held-out tree."""
    counts = {"public": 0, "heldout": 0}
    for d in docs:
        if d["split"] == "heldout":
            if heldout_dir is None:
                raise RuntimeError("held-out pairs generated but no held-out directory given")
            target = heldout_dir
        else:
            target = public_dir
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{d['pair_id']}.yaml").write_text(
            yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=100),
            encoding="utf-8",
            newline="\n",
        )
        counts[d["split"]] += 1
    return counts
