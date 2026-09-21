"""Item schema. The pydantic model is the single source of truth; the JSON Schema in
data/item.schema.json is generated from it (`flembench schema`)."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "0.1.0"


class Variety(StrEnum):
    BE = "be"
    NL = "nl"


class Track(StrEnum):
    A = "A"  # language gap
    B = "B"  # context gap
    C = "C"  # variety identification (diagnostic)
    D = "D"  # generation in register
    H = "H"  # hard dialect subset


CATEGORY_TRACK = {
    "A1": Track.A,
    "A2": Track.A,
    "B1": Track.B,
    "B2": Track.B,
    "C1": Track.C,
    "D1": Track.D,
    "H1": Track.H,
}
PAIRED_CATEGORIES = {"A1", "A2", "B1"}


class Register(StrEnum):
    STANDARD = "standard"
    TUSSENTAAL = "tussentaal"
    DIALECT = "dialect"


class Format(StrEnum):
    MC = "mc"
    EXACT = "exact"
    EXTRACTION = "extraction"
    GENERATION = "generation"


class MatchBasis(StrEnum):
    DCP_PREVALENCE = "dcp_prevalence"
    FUNCTIONAL_ANALOGUE = "functional_analogue"
    AUTHOR_JUDGEMENT = "author_judgement"


class Provenance(StrEnum):
    HUMAN_WRITTEN = "human_written"
    LLM_DRAFTED_HUMAN_VERIFIED = "llm_drafted_human_verified"


class Split(StrEnum):
    PUBLIC = "public"
    HELDOUT = "heldout"


DEFAULT_SCORER = {
    Format.MC: "mc_letter",
    Format.EXACT: "norm_exact",
    Format.EXTRACTION: "norm_extract",
    Format.GENERATION: "rubric",
}


class SecondReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer: str
    answer: str
    agrees_with_gold: bool
    context_gives_away_meaning: bool | None = None
    notes: str = ""


class Item(BaseModel):
    model_config = ConfigDict(
        extra="forbid", use_enum_values=True, validate_by_name=True, validate_by_alias=True
    )

    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    schema_version: str = SCHEMA_VERSION
    pair_id: str | None = None
    variety: Variety
    track: Track
    category: str
    subcategory: str | None = None
    register_level: Register = Field(default=Register.STANDARD, alias="register")
    marker: str | None = None
    prompt: str = Field(min_length=1)
    format: Format
    choices: list[str] | None = None
    gold: str
    accepted_variants: list[str] = Field(default_factory=list)
    scoring_method: str | None = None
    rubric: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    match_basis: MatchBasis | None = None
    lexical_source: str | None = None
    source: str | None = None
    licence: str | None = None
    valid_as_of: date | None = None
    provenance: Provenance
    drafted_by: str | None = None
    author: str
    reviewed_by: list[str] = Field(default_factory=list)
    second_review: SecondReview | None = None
    split: Split = Split.PUBLIC
    notes: str = ""

    @model_validator(mode="after")
    def _check(self) -> Item:
        errors: list[str] = []
        if self.category not in CATEGORY_TRACK:
            errors.append(f"unknown category {self.category!r}")
        elif CATEGORY_TRACK[self.category] != self.track:
            errors.append(
                f"category {self.category} belongs to track {CATEGORY_TRACK[self.category]}"
            )
        if self.format == Format.MC:
            if not self.choices or len(self.choices) < 2:
                errors.append("mc items need at least 2 choices")
            elif len(set(self.choices)) != len(self.choices):
                errors.append("mc choices must be distinct")
            elif self.gold not in letters(len(self.choices)):
                errors.append(f"mc gold must be a letter in {letters(len(self.choices))}")
        elif self.choices:
            errors.append("choices only allowed for mc items")
        if self.format == Format.GENERATION and not self.rubric:
            errors.append("generation items need a rubric")
        if self.category in PAIRED_CATEGORIES and not self.pair_id:
            errors.append(f"category {self.category} is paired: pair_id required")
        if self.pair_id and not self.match_basis:
            errors.append("paired items need match_basis")
        if self.track == Track.B and not self.valid_as_of:
            errors.append("track B items need valid_as_of")
        if self.provenance == Provenance.LLM_DRAFTED_HUMAN_VERIFIED and not self.drafted_by:
            errors.append("llm-drafted items need drafted_by (model id)")
        if self.source and not self.licence:
            errors.append("items with a source need a licence")
        if errors:
            raise ValueError("; ".join(errors))
        if self.scoring_method is None:
            self.scoring_method = DEFAULT_SCORER[Format(self.format)]
        return self


def letters(n: int) -> list[str]:
    return [chr(ord("A") + i) for i in range(n)]
