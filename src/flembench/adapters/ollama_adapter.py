from __future__ import annotations

import os
from typing import Any

import httpx

from flembench.adapters.base import Completion


class OllamaAdapter:
    """Local models through Ollama's native API, which reports the weight digest —
    the only reliable identifier for a quantised local model."""

    def __init__(self, client: httpx.Client | None = None, host: str | None = None):
        self.host = (host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self.client = client or httpx.Client(timeout=600)
        self._digests: dict[str, str] = {}

    def digest(self, model_id: str) -> str | None:
        if model_id not in self._digests:
            r = self.client.get(f"{self.host}/api/tags")
            r.raise_for_status()
            for m in r.json().get("models", []):
                self._digests[m["name"]] = m.get("digest", "")
        return self._digests.get(model_id)

    def complete(
        self, model_id: str, system: str, user: str, max_tokens: int, params: dict[str, Any]
    ) -> Completion:
        body = {
            "model": model_id,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "options": {**params, "num_predict": max_tokens},
        }
        r = self.client.post(f"{self.host}/api/chat", json=body)
        r.raise_for_status()
        d = r.json()
        return Completion(
            text=d["message"]["content"],
            input_tokens=d.get("prompt_eval_count", 0),
            output_tokens=d.get("eval_count", 0),
            model_reported=f"{model_id}@{self.digest(model_id)}",
            stop_reason=d.get("done_reason"),
        )
