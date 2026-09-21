from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from flembench.adapters.base import Completion
from flembench.paths import ROOT

# Keys in a model's params that configure prompt rendering rather than sampling.
TEMPLATE_KEYS = ("chat_template", "chat_template_sha256", "bos_token", "eos_token")
# Keys that go at the top level of the request body instead of into `options`.
TOP_LEVEL_KEYS = ("think",)


@lru_cache
def _template(path: str):
    from jinja2.sandbox import ImmutableSandboxedEnvironment

    # Same settings transformers uses for apply_chat_template.
    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)

    def raise_exception(msg: str):
        raise ValueError(msg)

    env.globals["raise_exception"] = raise_exception
    return env.from_string((ROOT / path).read_text(encoding="utf-8"))


def render_chat(path: str, system: str, user: str, bos_token: str = "", eos_token: str = "") -> str:
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    return _template(path).render(
        messages=messages, add_generation_prompt=True, bos_token=bos_token, eos_token=eos_token
    )


class OllamaAdapter:
    """Local models through Ollama's native API, which reports the weight digest —
    the only reliable identifier for a quantised local model.

    If params contain `chat_template`, the prompt is rendered from the model's *original*
    chat template and sent raw, bypassing the template embedded in a community GGUF.
    Otherwise Ollama's own template is used (for official Ollama-library models)."""

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
        options = {
            k: v for k, v in params.items() if k not in TEMPLATE_KEYS and k not in TOP_LEVEL_KEYS
        }
        options["num_predict"] = max_tokens
        if "chat_template" in params:
            eos = params.get("eos_token", "")
            if eos:
                options["stop"] = sorted({*options.get("stop", []), eos})
            prompt = render_chat(
                params["chat_template"], system, user, params.get("bos_token", ""), eos
            )
            body = {"model": model_id, "prompt": prompt, "raw": True, "stream": False}
            path, text_of = "/api/generate", lambda d: d["response"]
        else:
            messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
            body = {"model": model_id, "messages": messages, "stream": False}
            path, text_of = "/api/chat", lambda d: d["message"]["content"]
        body["options"] = options
        body |= {k: params[k] for k in TOP_LEVEL_KEYS if k in params}
        r = self.client.post(f"{self.host}{path}", json=body)
        r.raise_for_status()
        d = r.json()
        num_ctx = options.get("num_ctx")
        if num_ctx and d.get("prompt_eval_count", 0) + max_tokens > num_ctx:
            raise ContextOverflow(
                f"{model_id}: prompt of {d.get('prompt_eval_count')} tokens + {max_tokens} "
                f"output tokens exceeds num_ctx={num_ctx}; Ollama would truncate silently"
            )
        return Completion(
            text=text_of(d),
            input_tokens=d.get("prompt_eval_count", 0),
            output_tokens=d.get("eval_count", 0),
            model_reported=f"{model_id}@{self.digest(model_id)}",
            stop_reason=d.get("done_reason"),
        )


class ContextOverflow(RuntimeError):
    pass


def template_sha256(path: str) -> str:
    import hashlib

    return hashlib.sha256((ROOT / Path(path)).read_bytes()).hexdigest()
