"""Plan, estimate, execute and score runs. Execution only ever fills the cache;
scoring only ever reads it."""

from __future__ import annotations

import csv
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from flembench import cache
from flembench.adapters import Adapter, Completion, make_adapter
from flembench.prompts import PROMPT_VERSION, render
from flembench.registry import ModelSpec
from flembench.schema import Format, Item
from flembench.scoring import score

MAX_TOKENS = {Format.MC: 1024, Format.EXACT: 1024, Format.EXTRACTION: 1024, Format.GENERATION: 4096}
# Expected visible output per format, for the cost estimate only.
EXPECTED_OUT = {Format.MC: 5, Format.EXACT: 30, Format.EXTRACTION: 30, Format.GENERATION: 600}
CHARS_PER_TOKEN = 3.0  # conservative for Dutch


@dataclass
class Job:
    model: ModelSpec
    item: Item
    repeat: int
    system: str
    user: str
    max_tokens: int
    key: str
    root: Path

    @property
    def cached(self) -> dict | None:
        return cache.get(self.root, self.model.key, self.key)


def plan(items: Iterable[Item], models: Iterable[ModelSpec], repeats: int = 1) -> list[Job]:
    jobs = []
    for m in models:
        for it in items:
            system, user = render(it)
            max_tokens = MAX_TOKENS[Format(it.format)]
            for r in range(repeats):
                key = cache.cache_key(m.model_id, m.params, system, user, max_tokens, r)
                jobs.append(
                    Job(m, it, r, system, user, max_tokens, key, cache.cache_root(it.split))
                )
    return jobs


@dataclass
class Estimate:
    model: str
    calls: int
    cached: int
    expected_usd: float
    worst_case_usd: float


def estimate(jobs: list[Job]) -> list[Estimate]:
    out: dict[str, Estimate] = {}
    for j in jobs:
        e = out.setdefault(j.model.key, Estimate(j.model.key, 0, 0, 0.0, 0.0))
        if j.cached:
            e.cached += 1
            continue
        e.calls += 1
        tin = (len(j.system) + len(j.user)) / CHARS_PER_TOKEN + 20
        e.expected_usd += j.model.cost_usd(int(tin), EXPECTED_OUT[Format(j.item.format)]) * 2
        e.worst_case_usd += j.model.cost_usd(int(tin), j.max_tokens)
    return list(out.values())


# Provider errors that are worth waiting out (overload, rate limit), as opposed to permanent
# ones (no credits, invalid request) that must stop the run immediately.
_TRANSIENT = ("503", "unavailable", "overloaded", "high demand", "529", "rate limit", "timeout")
_PERMANENT = ("insufficient_quota", "credit_balance", "invalid_argument", "400", "401", "403")
RETRY_WAITS = (10, 30, 60, 120, 240)


def is_transient(exc: Exception) -> bool:
    msg = f"{type(exc).__name__} {exc}".lower()
    if any(p in msg for p in _PERMANENT):
        return False
    return any(t in msg for t in _TRANSIENT)


def call_with_retry(fn: Callable[[], Completion], sleep: Callable[[float], None] = time.sleep):
    for wait in (*RETRY_WAITS, None):
        try:
            return fn()
        except Exception as exc:
            if wait is None or not is_transient(exc):
                raise
            sleep(wait)
    raise AssertionError("unreachable")


def execute(
    jobs: list[Job],
    budget_usd: float,
    adapter_factory: Callable[[str], Adapter] = make_adapter,
    progress: Callable[[Job, dict], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> float:
    """Run uncached jobs; stop before exceeding the budget. Returns USD spent."""
    adapters: dict[str, Adapter] = {}
    spent = 0.0
    for j in jobs:
        if j.cached:
            continue
        if spent >= budget_usd:
            raise BudgetExceeded(f"budget ${budget_usd:.2f} reached after ${spent:.4f}")
        adapter = adapters.setdefault(j.model.provider, adapter_factory(j.model.provider))
        c = call_with_retry(
            partial(
                adapter.complete, j.model.model_id, j.system, j.user, j.max_tokens, j.model.params
            ),
            sleep=sleep,
        )
        cost = j.model.cost_usd(c.input_tokens, c.output_tokens)
        spent += cost
        entry = {
            "model_key": j.model.key,
            "model_id": j.model.model_id,
            "provider": j.model.provider,
            "params": j.model.params,
            "reasoning": j.model.reasoning,
            "item_id": j.item.id,
            "repeat": j.repeat,
            "prompt_version": PROMPT_VERSION,
            "max_tokens": j.max_tokens,
            "system": j.system,
            "user": j.user,
            "completion": c.to_dict(),
            "cost_usd": cost,
        }
        cache.put(j.root, j.model.key, j.key, entry)
        if progress:
            progress(j, entry)
    return spent


class BudgetExceeded(RuntimeError):
    pass


SCORE_FIELDS = [
    "model",
    "item_id",
    "pair_id",
    "variety",
    "category",
    "subcategory",
    "register",
    "split",
    "provenance",
    "repeat",
    "correct",
    "parse",
    "contains_gold",
    "parsed",
    "response",
    "input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "cost_usd",
    "model_reported",
]


def score_rows(jobs: list[Job]) -> list[dict]:
    rows = []
    for j in jobs:
        entry = j.cached
        if entry is None:
            continue
        c = entry["completion"]
        s = score(j.item, c["text"])
        it = j.item
        rows.append(
            {
                "model": j.model.key,
                "item_id": it.id,
                "pair_id": it.pair_id,
                "variety": it.variety,
                "category": it.category,
                "subcategory": it.subcategory,
                "register": it.register_level,
                "split": it.split,
                "provenance": it.provenance,
                "repeat": j.repeat,
                "correct": s.correct,
                "parse": s.parse,
                "contains_gold": s.contains_gold,
                "parsed": s.parsed,
                "response": c["text"],
                "input_tokens": c["input_tokens"],
                "output_tokens": c["output_tokens"],
                "reasoning_tokens": c["reasoning_tokens"],
                "cost_usd": entry["cost_usd"],
                "model_reported": c["model_reported"],
            }
        )
    return rows


def write_scores(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SCORE_FIELDS)
        w.writeheader()
        w.writerows(rows)
