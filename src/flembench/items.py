"""Load authored YAML item files, validate them, and compile to JSONL.

Authoring format (one file per pair, or per unpaired item), see items/_templates/:

    pair_id: a1-0001            # or `id:` for an unpaired item
    category: A1
    format: mc
    ...shared fields...
    be: {prompt: ..., choices: [CORRECT, distractor, ...], ...}
    nl: {prompt: ..., choices: [CORRECT, distractor, ...], ...}

For mc items the author always lists the correct answer FIRST. Compilation shuffles the
choices deterministically from the pair id, putting the gold answer at the same position
for both members of a pair, so answer position can never create a BE/NL difference.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from flembench.paths import COMPILED_ITEMS, ITEMS_DIR
from flembench.schema import CATEGORY_TRACK, PAIRED_CATEGORIES, Format, Item, Split, letters

VARIETY_KEYS = ("be", "nl")
HELDOUT_ENV = "FLEMBENCH_HELDOUT_DIR"


@dataclass
class LoadResult:
    items: list[Item] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _seed(key: str) -> int:
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "big")


def shuffle_choices(key: str, choices: list[str]) -> tuple[list[str], str]:
    """Return (shuffled choices, gold letter). choices[0] is the correct answer."""
    seed = _seed(key)
    n = len(choices)
    gold_pos = seed % n
    distractors = list(choices[1:])
    random.Random(seed).shuffle(distractors)
    out = distractors[:gold_pos] + [choices[0]] + distractors[gold_pos:]
    return out, letters(n)[gold_pos]


def build_items(doc: dict) -> list[Item]:
    doc = dict(doc)
    members = {k: doc.pop(k) for k in VARIETY_KEYS if k in doc}
    if not members:
        raise ValueError("file defines no `be:` or `nl:` block")
    pair_id = doc.pop("pair_id", None)
    item_id = doc.pop("id", None)
    if pair_id and item_id:
        raise ValueError("use either pair_id (paired) or id (unpaired), not both")
    if pair_id and set(members) != set(VARIETY_KEYS):
        raise ValueError("a pair needs both `be:` and `nl:`")
    if not pair_id and len(members) != 1:
        raise ValueError("an unpaired item file must have exactly one variety block")
    category = doc.get("category")
    if category not in CATEGORY_TRACK:
        raise ValueError(f"unknown category {category!r}")
    doc.setdefault("track", CATEGORY_TRACK[category].value)
    key = pair_id or item_id

    items = []
    for variety, fields in members.items():
        data = {**doc, **(fields or {}), "variety": variety, "pair_id": pair_id}
        data["id"] = f"{pair_id}-{variety}" if pair_id else item_id
        if data.get("format") == Format.MC.value:
            if "gold" in data:
                raise ValueError("mc items: list the correct answer first, do not set gold")
            if data.get("choices"):
                data["choices"], data["gold"] = shuffle_choices(key, data["choices"])
        items.append(Item.model_validate(data))
    return items


def check_pairs(items: list[Item]) -> list[str]:
    errors = []
    by_pair: dict[str, list[Item]] = {}
    for it in items:
        if it.pair_id:
            by_pair.setdefault(it.pair_id, []).append(it)
    for pid, members in by_pair.items():
        a, b = members
        for attr in ("category", "subcategory", "format", "split", "match_basis"):
            if getattr(a, attr) != getattr(b, attr):
                errors.append(f"{pid}: members differ in {attr}")
        if a.format == Format.MC and len(a.choices or []) != len(b.choices or []):
            errors.append(f"{pid}: members have different numbers of choices")
    ids = Counter(it.id for it in items)
    errors += [f"duplicate id {i}" for i, n in ids.items() if n > 1]
    return errors


def load_dir(directory: Path, expected_split: Split) -> LoadResult:
    result = LoadResult()
    for path in sorted(directory.rglob("*.yaml")):
        if any(part.startswith("_") for part in path.relative_to(directory).parts):
            continue  # templates and drafts
        rel = path.relative_to(directory).as_posix()
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise ValueError("file is not a YAML mapping")
            new = build_items(doc)
        except (ValueError, ValidationError, yaml.YAMLError) as e:
            result.errors.append(f"{rel}: {_fmt(e)}")
            continue
        for it in new:
            if it.split != expected_split.value:
                result.errors.append(
                    f"{rel}: split={it.split} but file lives in the {expected_split.value} tree"
                )
        result.items += new
    result.errors += check_pairs(result.items)
    return result


def load_all(include_heldout: bool = True) -> LoadResult:
    result = load_dir(ITEMS_DIR, Split.PUBLIC)
    heldout = os.environ.get(HELDOUT_ENV)
    if include_heldout and heldout:
        h = load_dir(Path(heldout) / "items", Split.HELDOUT)
        result.items += h.items
        result.errors += h.errors + check_pairs(result.items)
    return result


def write_jsonl(items: list[Item], path: Path = COMPILED_ITEMS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for it in sorted(items, key=lambda i: i.id):
            f.write(
                json.dumps(it.model_dump(mode="json", by_alias=True), ensure_ascii=False) + "\n"
            )


def read_jsonl(path: Path = COMPILED_ITEMS) -> list[Item]:
    with path.open(encoding="utf-8") as f:
        return [Item.model_validate_json(line) for line in f if line.strip()]


def summary(items: list[Item]) -> dict:
    paired = {i.pair_id for i in items if i.pair_id}
    gold_pos = Counter(i.gold for i in items if i.format == Format.MC and i.variety == "be")
    return {
        "items": len(items),
        "pairs": len(paired),
        "by_category": dict(sorted(Counter(i.category for i in items).items())),
        "by_provenance": dict(Counter(i.provenance for i in items)),
        "mc_gold_positions": dict(sorted(gold_pos.items())),
        "paired_categories_without_pairs": sorted(
            PAIRED_CATEGORIES - {i.category for i in items if i.pair_id}
        ),
    }


def _fmt(e: Exception) -> str:
    if isinstance(e, ValidationError):
        return "; ".join(
            f"{'.'.join(map(str, err['loc'])) or 'item'}: {err['msg']}" for err in e.errors()
        )
    return str(e)
