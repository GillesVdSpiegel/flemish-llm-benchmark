"""Check that local models see the same token sequence length as their original tokenizer.

For each templated local model: render a chat prompt with the harness, count its tokens with the
model's ORIGINAL Hugging Face tokenizer (respecting its BOS configuration), and compare with the
prompt_eval_count Ollama reports. A mismatch means a missing or doubled BOS token or a
template/tokenizer discrepancy, which would silently handicap the model.

    uv run --with tokenizers python scripts/check_local_tokenization.py

Result on 2026-09-21 (Ollama 0.34.2): all three OK.
"""

from __future__ import annotations

import sys

import httpx
from tokenizers import Tokenizer

from flembench.adapters.ollama_adapter import render_chat
from flembench.registry import load_registry

ORIGINALS = {
    "eurollm-9b": "utter-project/EuroLLM-9B-Instruct-2512",
    "geitje-7b-ultra": "BramVanroy/GEITje-7B-ultra",
    "chocollama-8b": "ChocoLlama/Llama-3-ChocoLlama-8B-instruct",
}
SYSTEM, USER = "Je beantwoordt vragen.", "Wat betekent dit woord?"


def main() -> int:
    reg = load_registry()
    http = httpx.Client(timeout=600, follow_redirects=True)
    failures = 0
    for key, repo in ORIGINALS.items():
        spec = reg[key]
        p = spec.params
        cfg = http.get(f"https://huggingface.co/{repo}/resolve/main/tokenizer_config.json").json()
        tok = Tokenizer.from_str(
            http.get(f"https://huggingface.co/{repo}/resolve/main/tokenizer.json").text
        )
        prompt = render_chat(p["chat_template"], SYSTEM, USER, p["bos_token"], p["eos_token"])
        n = len(tok.encode(prompt, add_special_tokens=False).ids)
        # transformers' fast Llama tokenizers honour add_bos_token; None means the
        # tokenizer.json post-processor decides (Llama 3 adds <|begin_of_text|>).
        add_bos = cfg.get("add_bos_token")
        expected = len(tok.encode(prompt).ids) if add_bos is None else n + bool(add_bos)
        r = http.post(
            "http://localhost:11434/api/generate",
            json={
                "model": spec.model_id,
                "prompt": prompt,
                "raw": True,
                "stream": False,
                "options": {"num_predict": 1, "temperature": 0, "num_ctx": 4096},
            },
        ).json()
        got = r["prompt_eval_count"]
        ok = got == expected
        failures += not ok
        print(f"{'OK ' if ok else 'BAD'} {key:<16} original={expected:<4} ollama={got}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
