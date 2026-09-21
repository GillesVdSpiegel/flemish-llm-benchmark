# Authoring guide

All commands run from the repo root. First time: `python -m uv sync --all-extras`
(or `uv sync` if `uv` is on your PATH). Prefix commands with `uv run`.

## 1. Lexicon candidates (A1a)

```
uv run flembench lexicon candidates    # downloads the norms once, ~1 min
uv run flembench lexicon curate        # one key per word; saved after every key
uv run flembench lexicon pair          # after curating: prevalence-matched pairs
```

Curation keys:

| key | decision | use when |
|---|---|---|
| `k` | keep | opaque, current, variety-specific. Then pick a register (`s`/`t`/`d`) and type a short gloss. |
| `t` | reject_transparent | a Dutch reader could work out the meaning from the form (*recycleren*) |
| `n` | reject_not_specific | the meaning is not variety-specific |
| `b` | reject_brand_or_name | brand or proper name (*vlaflip*, *kliko*) |
| `o` | reject_obsolete | obsolete or too rare |
| `d` | reject_duplicate | inflection or spelling variant of another candidate |
| `a` | move_to_b1 | institution or abbreviation (*kmo*, *vmbo*) — belongs in B1 |
| `u` | needs_other_variety_speaker | you don't know it — goes to the Netherlands reviewer |
| space / `z` / `q` | skip / undo / quit | |

Words are shown in a seeded random order, alternating BE and NL, without prevalence numbers
(to avoid anchoring). You can stop at any time and resume where you left off. Decisions live in
`data/curation/lexicon_decisions.csv`, which is committed; the prevalence values are not.

## 2. Writing items

1. Copy a template from `items/_templates/` into the category folder, e.g.
   `items/A1/a1-0001.yaml`. The file name does not matter; the `pair_id`/`id` does.
2. For multiple choice, put the **correct answer first**. The compiler shuffles the options and
   gives both members of a pair the same answer position.
3. Keep A1 context sentences **uninformative**: the sentence must not reveal the meaning.
4. No real names, addresses, national register numbers or case details. Letters are fictional.
5. If an LLM drafted any part, set `provenance: llm_drafted_human_verified` and
   `drafted_by: <model id>`.
6. Check your work:

```
uv run flembench validate
```

Anything under a folder or file starting with `_` is ignored (use `items/A1/_drafts/` for
unfinished work).

## 3. Pilot targets (Phase 1)

| Category | Pilot |
|---|---|
| A1 | 10 pairs |
| A2 | 5 pairs |
| B1 | 10 pairs |
| C1 | 10 items (5 BE, 5 NL) |
| D1 | 3 prompts |

Then: `uv run flembench estimate claude-sonnet-5` → `uv run flembench run claude-sonnet-5 --budget 0.20`
→ `uv run flembench rescore`.
