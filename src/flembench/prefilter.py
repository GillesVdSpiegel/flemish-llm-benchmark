"""Optional LLM prefilter for lexicon candidates — form-based rejections only.

LLMs are asked ONLY whether a word is a brand, a proper name or an abbreviation. They are never
asked about meaning, regional origin or quality, and they can never accept a word: an LLM can
only confidently "accept" words it knows, which would bias the benchmark towards words models
already know and shrink the gap it measures.

A word is auto-decided only when at least MIN_MODELS different models all return the same
non-NONE category. A seeded AUDIT_SHARE of those auto-decisions is held back and curated
blind by the author; `prefilter-report` then gives the prefilter's agreement with the author.

Files (all committed; words and verdicts only, no prevalence values):
    data/curation/prefilter/PROMPT.md           the prompt to paste
    data/curation/prefilter/words.csv           id, variety, word
    data/curation/prefilter/batches/NN.txt      id;word lines to paste after the prompt
    data/curation/prefilter/results/<model>__NN.txt   raw model output, one file per batch
    data/curation/prefilter/audit.csv           held-back auto-decisions for blind checking
"""

from __future__ import annotations

import csv
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from flembench.paths import CURATION_DIR

DIR = CURATION_DIR / "prefilter"
WORDS_FILE = DIR / "words.csv"
BATCH_DIR = DIR / "batches"
RESULTS_DIR = DIR / "results"
AUDIT_FILE = DIR / "audit.csv"
PROMPT_FILE = DIR / "PROMPT.md"

CATEGORY_DECISION = {
    "BRAND": "reject_brand_or_name",
    "NAME": "reject_brand_or_name",
    "ABBR": "move_to_b1",
    "NONE": None,
}
MIN_MODELS = 2
AUDIT_SHARE = 0.10
MIN_AUDIT = 5

PROMPT = """\
You are helping clean a list of Dutch words, from both Belgium and the Netherlands, before a
linguist reviews every remaining word by hand.

For each word, decide ONLY whether it belongs to one of these form-based categories:

BRAND  a brand, trademark or commercial product name
NAME   a proper noun: a person, place, organisation, institution name or event
ABBR   an abbreviation, acronym or initialism
NONE   none of the above: any ordinary word, including dialect, slang, informal words,
       loanwords, and any word you do not recognise

Rules:
- Do NOT judge meaning, correctness, spelling, regional origin, register or how common a
  word is. Those are not your task.
- If you do not recognise a word, answer NONE.
- If you are unsure, answer NONE. Only use BRAND, NAME or ABBR when you are confident.
- Output exactly one line per input line, in the same order, in the form id;CATEGORY
- Output nothing else: no header, no explanation, no code fences.

Words:
"""


@dataclass
class Word:
    id: str
    variety: str
    word: str


# ------------------------------------------------------------------ export


def export(
    candidates: list[tuple[str, str]], batch_size: int = 200, seed: int = 0, root: Path = DIR
) -> list[Path]:
    """Shuffle (so batches mix BE and NL and carry no ordering signal), assign neutral ids,
    and write the prompt, the id map and the batch files. Varieties are not shown to models."""
    items = sorted(set(candidates))
    random.Random(seed).shuffle(items)
    words = [Word(f"w{i + 1:04d}", v, w) for i, (v, w) in enumerate(items)]
    root.mkdir(parents=True, exist_ok=True)
    (root / "PROMPT.md").write_text(PROMPT, encoding="utf-8", newline="\n")
    with (root / "words.csv").open("w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f, lineterminator="\n")
        wr.writerow(["id", "variety", "word"])
        wr.writerows((x.id, x.variety, x.word) for x in words)
    batch_dir = root / "batches"
    batch_dir.mkdir(exist_ok=True)
    paths = []
    for n, start in enumerate(range(0, len(words), batch_size), start=1):
        p = batch_dir / f"{n:02d}.txt"
        chunk = words[start : start + batch_size]
        p.write_text("".join(f"{x.id};{x.word}\n" for x in chunk), encoding="utf-8", newline="\n")
        paths.append(p)
    return paths


# ------------------------------------------------------------------ import

_LINE = re.compile(r"^\s*(w\d{4})\s*[;,:\t|]\s*([A-Za-z]+)\s*$")


def parse_output(text: str) -> tuple[dict[str, str], list[str]]:
    """Return ({id: CATEGORY}, problems). Tolerates code fences and blank lines."""
    out: dict[str, str] = {}
    problems = []
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("```"):
            continue
        m = _LINE.match(line)
        if not m:
            problems.append(f"unparseable line: {line.strip()[:60]!r}")
            continue
        wid, cat = m[1], m[2].upper()
        if cat not in CATEGORY_DECISION:
            problems.append(f"{wid}: unknown category {cat}")
            continue
        out[wid] = cat
    return out, problems


def load_words(root: Path = DIR) -> dict[str, Word]:
    with (root / "words.csv").open(encoding="utf-8", newline="") as f:
        return {r["id"]: Word(r["id"], r["variety"], r["word"]) for r in csv.DictReader(f)}


def load_results(root: Path = DIR) -> tuple[dict[str, dict[str, str]], list[str]]:
    """{model: {id: CATEGORY}} from results/<model>__<batch>.txt, plus problems found."""
    verdicts: dict[str, dict[str, str]] = defaultdict(dict)
    problems = []
    for p in sorted((root / "results").glob("*.txt")):
        if "__" not in p.stem:
            problems.append(f"{p.name}: name must be <model>__<batch>.txt")
            continue
        model = p.stem.split("__")[0]
        parsed, probs = parse_output(p.read_text(encoding="utf-8"))
        batch = p.stem.split("__")[1]
        expected = _batch_ids(root, batch)
        if expected is not None:
            missing = expected - parsed.keys()
            extra = parsed.keys() - expected
            if missing:
                probs.append(f"{len(missing)} ids missing (e.g. {sorted(missing)[:3]})")
            if extra:
                probs.append(f"{len(extra)} ids not in batch {batch}")
                parsed = {k: v for k, v in parsed.items() if k in expected}
        problems += [f"{p.name}: {x}" for x in probs]
        verdicts[model].update(parsed)
    return dict(verdicts), problems


def _batch_ids(root: Path, batch: str) -> set[str] | None:
    p = root / "batches" / f"{batch}.txt"
    if not p.exists():
        return None
    return {line.split(";")[0] for line in p.read_text(encoding="utf-8").splitlines() if line}


def unanimous(verdicts: dict[str, dict[str, str]]) -> dict[str, tuple[str, list[str]]]:
    """{id: (CATEGORY, models)} for ids where >= MIN_MODELS models all gave the same
    non-NONE category. Any dissent, any NONE, or too few models -> left to the author."""
    by_id: dict[str, dict[str, str]] = defaultdict(dict)
    for model, v in verdicts.items():
        for wid, cat in v.items():
            by_id[wid][model] = cat
    out = {}
    for wid, votes in by_id.items():
        cats = set(votes.values())
        if len(votes) >= MIN_MODELS and len(cats) == 1 and "NONE" not in cats:
            out[wid] = (cats.pop(), sorted(votes))
    return out


def split_audit(ids: list[str], seed: int = 0) -> tuple[set[str], set[str]]:
    """Return (auto, audit). The audit sample is curated blind by the author."""
    ids = sorted(ids)
    k = min(len(ids), max(MIN_AUDIT, round(len(ids) * AUDIT_SHARE)))
    audit = set(random.Random(seed).sample(ids, k))
    return set(ids) - audit, audit


def apply(
    decided: dict[tuple[str, str], dict], root: Path = DIR, seed: int = 0
) -> tuple[dict[tuple[str, str], dict], dict]:
    """Merge unanimous prefilter verdicts into the decisions. Author decisions always win."""
    words = load_words(root)
    verdicts, problems = load_results(root)
    agreed = unanimous(verdicts)
    auto, audit = split_audit(list(agreed), seed)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    # Re-importing recomputes every prefilter decision from scratch.
    decided = {k: v for k, v in decided.items() if v.get("decided_by") != "llm_prefilter"}
    added = 0
    for wid in sorted(auto):
        w = words[wid]
        key = (w.variety, w.word)
        if key in decided:  # the author already decided this word
            continue
        cat, models = agreed[wid]
        decided[key] = {
            "variety": w.variety, "word": w.word, "decision": CATEGORY_DECISION[cat],
            "register": "", "gloss": "", "note": f"prefilter {cat}: {', '.join(models)}",
            "decided_by": "llm_prefilter", "decided_at": now,
        }  # fmt: skip
        added += 1
    with (root / "audit.csv").open("w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f, lineterminator="\n")
        wr.writerow(["id", "variety", "word", "llm_category", "models"])
        for wid in sorted(audit):
            w = words[wid]
            wr.writerow([wid, w.variety, w.word, agreed[wid][0], ", ".join(agreed[wid][1])])
    stats = {
        "models": sorted(verdicts),
        "words_with_any_verdict": len({i for v in verdicts.values() for i in v}),
        "unanimous_flags": len(agreed),
        "auto_decided": added,
        "held_back_for_blind_audit": len(audit),
        "problems": problems,
    }
    return decided, stats


def report(decided: dict[tuple[str, str], dict], root: Path = DIR) -> dict:
    """Agreement between the prefilter and the author on the blind audit sample."""
    if not (root / "audit.csv").exists():
        return {"error": "no audit.csv; run prefilter-import first"}
    with (root / "audit.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    done = [r for r in rows if (r["variety"], r["word"]) in decided]
    agree = [
        r for r in done
        if decided[(r["variety"], r["word"])]["decision"] == CATEGORY_DECISION[r["llm_category"]]
    ]  # fmt: skip
    return {
        "audit_size": len(rows),
        "curated_by_author": len(done),
        "agreement": f"{len(agree)}/{len(done)}" if done else "n/a",
        "disagreements": [
            f"{r['variety']}:{r['word']} llm={r['llm_category']} "
            f"author={decided[(r['variety'], r['word'])]['decision']}"
            for r in done
            if r not in agree
        ],
    }
