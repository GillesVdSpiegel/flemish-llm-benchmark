from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from flembench.paths import CONFIG_DIR


class Price(BaseModel):
    input: float
    output: float


class ModelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    provider: str
    model_id: str
    params: dict[str, Any] = {}
    reasoning: str
    price: Price

    def cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.price.input + output_tokens * self.price.output) / 1e6


def load_registry(path: Path = CONFIG_DIR / "models.yaml") -> dict[str, ModelSpec]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {k: ModelSpec(key=k, **v) for k, v in doc["models"].items()}
