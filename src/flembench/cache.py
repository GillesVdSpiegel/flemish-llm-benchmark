"""Response cache: one JSON file per (model, params, prompt, repeat). Re-scoring reads only
from here and never calls a provider. Held-out responses are cached in the private
held-out repo so their prompts never enter this repository."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flembench.paths import CACHE_DIR

HELDOUT_ENV = "FLEMBENCH_HELDOUT_DIR"


def cache_key(
    model_id: str, params: dict[str, Any], system: str, user: str, max_tokens: int, repeat: int
) -> str:
    payload = json.dumps(
        {
            "model_id": model_id,
            "params": params,
            "system": system,
            "user": user,
            "max_tokens": max_tokens,
            "repeat": repeat,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cache_root(split: str) -> Path:
    if split == "heldout":
        heldout = os.environ.get(HELDOUT_ENV)
        if not heldout:
            raise RuntimeError(f"held-out item but {HELDOUT_ENV} is not set")
        return Path(heldout) / "runs" / "cache"
    return CACHE_DIR


def entry_path(root: Path, model_key: str, key: str) -> Path:
    return root / model_key / key[:2] / f"{key}.json"


def get(root: Path, model_key: str, key: str) -> dict | None:
    p = entry_path(root, model_key, key)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def put(root: Path, model_key: str, key: str, entry: dict) -> None:
    p = entry_path(root, model_key, key)
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {**entry, "cached_at": datetime.now(UTC).isoformat(timespec="seconds")}
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    tmp.replace(p)
