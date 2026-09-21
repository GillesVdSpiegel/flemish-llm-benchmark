"""Instruction wrappers. Written in neutral Standard Dutch (no Belgian- or Netherlands-specific
words) and identical for BE and NL items and for every model. Changing any string here
changes every cache key, which is intended: a different prompt is a different experiment."""

from __future__ import annotations

from flembench.schema import Format, Item, letters

PROMPT_VERSION = "p1"

SYSTEM = (
    "Je beantwoordt vragen over Nederlandstalige teksten. Volg de antwoordinstructie nauwkeurig."
)

_INSTRUCTION = {
    Format.MC: "Antwoord met alleen de letter van het juiste antwoord ({letters}).",
    Format.EXACT: "Geef alleen het antwoord, zonder uitleg.",
    Format.EXTRACTION: "Geef alleen het gevraagde gegeven, zonder uitleg.",
    Format.GENERATION: "",
}


def render(item: Item) -> tuple[str, str]:
    """Return (system, user) messages for an item."""
    fmt = Format(item.format)
    parts = [item.prompt.strip()]
    if fmt == Format.MC:
        assert item.choices
        ls = letters(len(item.choices))
        parts.append(
            "\n".join(f"{letter}. {c}" for letter, c in zip(ls, item.choices, strict=True))
        )
        joined = ", ".join(ls[:-1]) + f" of {ls[-1]}"
        parts.append(_INSTRUCTION[fmt].format(letters=joined))
    elif _INSTRUCTION[fmt]:
        parts.append(_INSTRUCTION[fmt])
    return SYSTEM, "\n\n".join(parts)
