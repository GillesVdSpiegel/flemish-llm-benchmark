"""Download, verify and register the local models listed in config/local_models.yaml.

    uv run python scripts/setup_local_models.py            # all models
    uv run python scripts/setup_local_models.py geitje-7b-ultra

Idempotent: a file that exists with the right SHA-256 is not downloaded again, and an
interrupted download resumes. Requires a running Ollama server and `ollama` on PATH (or
OLLAMA_EXE pointing at the binary).
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "local_models.yaml"


def gguf_dir() -> Path:
    return Path(os.environ.get("FLEMBENCH_GGUF_DIR") or ROOT / "data" / "external" / "gguf")


def ollama_exe() -> str:
    exe = os.environ.get("OLLAMA_EXE") or shutil.which("ollama")
    if not exe:
        local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
        exe = str(local) if local.exists() else None
    if not exe:
        sys.exit("ollama not found: install it or set OLLAMA_EXE")
    return exe


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 24):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, size: int) -> None:
    done = dest.stat().st_size if dest.exists() else 0
    if done >= size:
        return
    headers = {"Range": f"bytes={done}-"} if done else {}
    with httpx.stream("GET", url, headers=headers, follow_redirects=True, timeout=60) as r:
        r.raise_for_status()
        with dest.open("ab") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
                done += len(chunk)
                print(f"\r  {done / 1e9:.2f} / {size / 1e9:.2f} GB", end="", flush=True)
    print()


def setup(name: str, spec: dict) -> None:
    print(f"== {name}")
    path = gguf_dir() / spec["file"]
    path.parent.mkdir(parents=True, exist_ok=True)
    download(
        f"https://huggingface.co/{spec['repo']}/resolve/main/{spec['file']}", path, spec["size"]
    )
    print("  verifying sha256 ...")
    digest = sha256(path)
    if digest != spec["sha256"]:
        sys.exit(f"  SHA-256 mismatch for {path}: {digest} (delete the file and retry)")
    with tempfile.TemporaryDirectory() as tmp:
        modelfile = Path(tmp) / "Modelfile"
        modelfile.write_text(f"FROM {path.as_posix()}\n", encoding="utf-8")
        subprocess.run(
            [ollama_exe(), "create", spec["ollama_name"], "-f", str(modelfile)], check=True
        )
    print(f"  registered as {spec['ollama_name']}")


def main() -> None:
    models = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["models"]
    wanted = sys.argv[1:] or list(models)
    for name in wanted:
        setup(name, models[name])


if __name__ == "__main__":
    main()
