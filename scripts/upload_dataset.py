"""Upload the public dataset and its card to a Hugging Face dataset repo.

    uv run --with huggingface_hub python scripts/upload_dataset.py --dry-run   # show what would go
    uv run --with huggingface_hub python scripts/upload_dataset.py             # upload

Uploads exactly two files, both already in this repository:
    data/items.jsonl      -> items.jsonl   (788 public questions)
    data/DATASET_CARD.md  -> README.md     (the dataset page)

Never uploads the held-out split, the raw model responses, or anything derived from the CC BY-NC
prevalence norms. Reads HF_TOKEN from .env; the token is never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "data" / "items.jsonl"
CARD = ROOT / "data" / "DATASET_CARD.md"
DEFAULT_REPO = "Goomey/flembench"


def check(items: Path) -> dict:
    """Refuse to upload anything that is not a public item."""
    rows = [json.loads(line) for line in items.read_text(encoding="utf-8").splitlines() if line]
    bad = [r["id"] for r in rows if r.get("split") != "public"]
    if bad:
        sys.exit(f"refusing to upload: {len(bad)} non-public items ({bad[:3]})")
    varieties = {r["variety"] for r in rows}
    return {"items": len(rows), "pairs": len({r["pair_id"] for r in rows}), "varieties": varieties}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    stats = check(ITEMS)
    print(f"repo:  {args.repo}")
    print(f"files: items.jsonl ({ITEMS.stat().st_size / 1024:.0f} kB), README.md from DATASET_CARD")
    varieties = sorted(stats["varieties"])
    print(f"data:  {stats['items']} items, {stats['pairs']} pairs, varieties {varieties}")
    if args.dry_run:
        print("dry run: nothing uploaded")
        return

    from dotenv import load_dotenv
    from huggingface_hub import HfApi

    load_dotenv(ROOT / ".env")
    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit("HF_TOKEN is not set in .env")
    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=ITEMS, path_in_repo="items.jsonl", repo_id=args.repo, repo_type="dataset"
    )
    api.upload_file(
        path_or_fileobj=CARD, path_in_repo="README.md", repo_id=args.repo, repo_type="dataset"
    )
    print(f"uploaded → https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    main()
