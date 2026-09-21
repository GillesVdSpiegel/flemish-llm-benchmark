from __future__ import annotations

from typing import Any

from flembench.adapters.base import Completion


class AnthropicAdapter:
    """Claude via the official SDK. Sonnet 5 rejects `temperature`; determinism is
    approximated with thinking disabled (set in config/models.yaml)."""

    def __init__(self, client: Any | None = None):
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self.client = client

    def complete(
        self, model_id: str, system: str, user: str, max_tokens: int, params: dict[str, Any]
    ) -> Completion:
        r = self.client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            **params,
        )
        text = "".join(b.text for b in r.content if b.type == "text")
        return Completion(
            text=text,
            input_tokens=r.usage.input_tokens,
            output_tokens=r.usage.output_tokens,
            model_reported=r.model,
            stop_reason=r.stop_reason,
            raw={"id": r.id},
        )
