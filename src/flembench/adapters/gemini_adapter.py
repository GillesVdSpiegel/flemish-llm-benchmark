from __future__ import annotations

from typing import Any

from flembench.adapters.base import Completion


class GeminiAdapter:
    """Gemini via google-genai. Use a *paid-tier* key: free-tier prompts may be used to
    improve Google's products, which would leak held-out items.

    params: temperature, thinking_level (MINIMAL/LOW/...), passed into the generation config.
    """

    def __init__(self, client: Any | None = None):
        if client is None:
            from google import genai

            client = genai.Client()
        self.client = client

    def complete(
        self, model_id: str, system: str, user: str, max_tokens: int, params: dict[str, Any]
    ) -> Completion:
        from google.genai import types

        params = dict(params)
        level = params.pop("thinking_level", None)
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            thinking_config=types.ThinkingConfig(thinking_level=level) if level else None,
            **params,
        )
        r = self.client.models.generate_content(model=model_id, contents=user, config=config)
        u = r.usage_metadata
        thoughts = u.thoughts_token_count or 0
        finish = r.candidates[0].finish_reason if r.candidates else None
        return Completion(
            text=r.text or "",
            input_tokens=u.prompt_token_count or 0,
            output_tokens=(u.candidates_token_count or 0) + thoughts,
            reasoning_tokens=thoughts,
            model_reported=r.model_version,
            stop_reason=str(finish) if finish is not None else None,
            raw={"id": r.response_id},
        )
