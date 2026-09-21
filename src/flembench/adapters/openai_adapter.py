from __future__ import annotations

from typing import Any

from flembench.adapters.base import Completion


class OpenAIAdapter:
    """OpenAI Responses API. Reasoning effort comes from config/models.yaml."""

    def __init__(self, client: Any | None = None):
        if client is None:
            import openai

            client = openai.OpenAI()
        self.client = client

    def complete(
        self, model_id: str, system: str, user: str, max_tokens: int, params: dict[str, Any]
    ) -> Completion:
        r = self.client.responses.create(
            model=model_id,
            instructions=system,
            input=user,
            max_output_tokens=max_tokens,
            store=False,
            **params,
        )
        details = getattr(r.usage, "output_tokens_details", None)
        return Completion(
            text=r.output_text or "",
            input_tokens=r.usage.input_tokens,
            output_tokens=r.usage.output_tokens,
            reasoning_tokens=getattr(details, "reasoning_tokens", 0) or 0,
            model_reported=r.model,
            stop_reason=r.status,
            raw={"id": r.id},
        )
