from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


@dataclass
class Completion:
    text: str
    input_tokens: int
    output_tokens: int  # billed output, including any reasoning tokens
    reasoning_tokens: int = 0
    model_reported: str | None = None  # model/version string or weight digest from the provider
    stop_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Adapter(Protocol):
    def complete(
        self, model_id: str, system: str, user: str, max_tokens: int, params: dict[str, Any]
    ) -> Completion: ...
