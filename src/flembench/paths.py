from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ITEMS_DIR = ROOT / "items"
DATA_DIR = ROOT / "data"
COMPILED_ITEMS = DATA_DIR / "items.jsonl"
SCHEMA_FILE = DATA_DIR / "item.schema.json"
EXTERNAL_DIR = DATA_DIR / "external"
DERIVED_DIR = DATA_DIR / "derived"  # gitignored: may contain CC BY-NC values
CURATION_DIR = DATA_DIR / "curation"  # committed: author decisions only
CONFIG_DIR = ROOT / "config"
RUNS_DIR = ROOT / "runs"
CACHE_DIR = RUNS_DIR / "cache"
