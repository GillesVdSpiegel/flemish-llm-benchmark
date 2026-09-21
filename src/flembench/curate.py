"""Keyboard-driven curation of lexicon candidates.

Decisions are appended to data/curation/lexicon_decisions.csv (committed). The file holds
only words and the author's judgements — no prevalence values — so it is licence-clean.
Prevalence numbers are deliberately not shown while curating, to avoid anchoring.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from flembench.paths import CURATION_DIR

DECISIONS_FILE = CURATION_DIR / "lexicon_decisions.csv"
FIELDS = ["variety", "word", "decision", "register", "gloss", "note", "decided_by", "decided_at"]

DECISIONS = {
    "k": ("keep", "keep — opaque, current, variety-specific"),
    "t": ("reject_transparent", "reject — meaning inferable from the form"),
    "n": ("reject_not_specific", "reject — meaning not variety-specific"),
    "b": ("reject_brand_or_name", "reject — brand or proper name"),
    "o": ("reject_obsolete", "reject — obsolete or too rare"),
    "d": ("reject_duplicate", "reject — inflection/duplicate of another candidate"),
    "a": ("move_to_b1", "move to B1 — institution/abbreviation"),
    "u": ("needs_other_variety_speaker", "I don't know it — send to a speaker of that variety"),
}
REGISTERS = {"s": "standard", "t": "tussentaal", "d": "dialect"}


@dataclass
class Candidate:
    variety: str
    word: str
    inflection_of: str | None = None


@dataclass
class Session:
    queue: list[Candidate]
    decided: dict[tuple[str, str], dict] = field(default_factory=dict)
    history: list[tuple[str, str]] = field(default_factory=list)

    @classmethod
    def create(cls, candidates: list[Candidate], decided: dict, seed: int = 0) -> Session:
        """Order: shuffled within variety (seeded), then interleaved BE/NL so both sides
        are curated at the same pace and fatigue does not correlate with prevalence."""
        rng = random.Random(seed)
        by_v = {v: [c for c in candidates if c.variety == v] for v in ("be", "nl")}
        for lst in by_v.values():
            rng.shuffle(lst)
        interleaved = [c for pair in _zip_longest(by_v["be"], by_v["nl"]) for c in pair if c]
        queue = [c for c in interleaved if (c.variety, c.word) not in decided]
        return cls(queue=queue, decided=dict(decided))

    @property
    def current(self) -> Candidate | None:
        return self.queue[0] if self.queue else None

    def decide(self, code: str, register: str = "", gloss: str = "", note: str = "") -> dict:
        c = self.queue.pop(0)
        row = {
            "variety": c.variety,
            "word": c.word,
            "decision": DECISIONS[code][0],
            "register": register,
            "gloss": gloss,
            "note": note,
            "decided_by": "author",
            "decided_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        self.decided[(c.variety, c.word)] = row
        self.history.append((c.variety, c.word))
        return row

    def skip(self) -> None:
        self.queue.append(self.queue.pop(0))

    def undo(self, candidates_by_key: dict[tuple[str, str], Candidate]) -> tuple[str, str] | None:
        if not self.history:
            return None
        key = self.history.pop()
        del self.decided[key]
        self.queue.insert(0, candidates_by_key[key])
        return key

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for row in self.decided.values():
            k = f"{row['variety']}:{row['decision']}"
            out[k] = out.get(k, 0) + 1
        return out


def _zip_longest(a: list, b: list):
    for i in range(max(len(a), len(b))):
        yield (a[i] if i < len(a) else None, b[i] if i < len(b) else None)


def load_decisions(path: Path = DECISIONS_FILE) -> dict[tuple[str, str], dict]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {(r["variety"], r["word"]): r for r in csv.DictReader(f)}


def save_decisions(decided: dict[tuple[str, str], dict], path: Path = DECISIONS_FILE) -> None:
    """Rewrite atomically, sorted, so the committed file diffs cleanly."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n", restval="")
        w.writeheader()
        for key in sorted(decided):
            w.writerow(decided[key])
    tmp.replace(path)
