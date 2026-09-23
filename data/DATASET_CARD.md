---
language:
  - nl
license: cc-by-4.0
task_categories:
  - multiple-choice
task_ids:
  - multiple-choice-qa
pretty_name: flembench — Belgian vs Netherlands Dutch vocabulary
size_categories:
  - n<1K
tags:
  - dutch
  - flemish
  - belgian-dutch
  - language-varieties
  - evaluation
configs:
  - config_name: default
    data_files: items.jsonl
---

# flembench — Belgian Dutch vs Netherlands Dutch vocabulary

788 multiple-choice questions (394 matched pairs) that measure whether a language model knows
Belgian-Dutch words as well as Netherlands-Dutch words **of the same difficulty for humans**.

Companion repository, code and full results:
[github.com/GillesVdSpiegel/flemish-llm-benchmark](https://github.com/GillesVdSpiegel/flemish-llm-benchmark).

## What makes this different

Existing Dutch evaluations (EuroEval, DUMB, the Amsterdam government benchmark) do not distinguish
the two varieties. The problem with any such comparison is confounding: if the Belgian questions
are simply harder, a lower score proves nothing.

Here, every Belgian word is **paired with a Netherlands word that is equally well known in its own
country**, using word prevalence norms measured separately for Belgium and the Netherlands
(Brysbaert et al. 2019). The mean difference within a pair is **0.6 percentage points**. A
difference in model scores is therefore a property of the model, not of the word list.

## Example

```json
{
  "id": "a1a-0437-be",
  "pair_id": "a1a-0437",
  "variety": "be",
  "marker": "velo",
  "prompt": "Wat betekent het woord \"velo\" zoals het in België gebruikt wordt?",
  "choices": ["fiets", "treuzelen", "hal, entree", "salarisschaal"],
  "gold": "A",
  "subcategory": "A1a-clean"
}
```

The Netherlands member of the pair uses the identical template ("… zoals het in Nederland gebruikt
wordt?"), and **the correct answer occupies the same position in both**, so a model's preference for
a particular letter cannot produce a gap.

## Fields

| Field | Meaning |
|---|---|
| `id`, `pair_id` | item id; both members of a pair share `pair_id` |
| `variety` | `be` (Belgian Dutch) or `nl` (Netherlands Dutch) |
| `marker` | the word being tested |
| `prompt`, `choices`, `gold` | question, four options, correct letter |
| `subcategory` | `A1a-clean` (602) or `A1a-overlap` (186, meaning resembles the word) |
| `register` | `standard`, `tussentaal` or `unspecified` |
| `drafted_by`, `reviewed_by`, `provenance` | where the correct answer came from |
| `split` | always `public` here; 20% of pairs are held out privately |

## How to use

```python
from datasets import load_dataset

ds = load_dataset("Goomey/flembench", split="train")
item = ds[0]
prompt = item["prompt"] + "\n\n" + "\n".join(
    f"{letter}. {choice}" for letter, choice in zip("ABCD", item["choices"])
)
# ask your model for a single letter, compare with item["gold"]
```

Report accuracy per `variety`, and the **gap** as the mean over pairs of
(Belgian correct − Netherlands correct). Use `subcategory == "A1a-clean"` for the headline figure.

## Baseline results (September 2026)

| Model | Belgian | Netherlands | Gap |
|---|---|---|---|
| Gemini 3.8 Flash | 98.7% | 100.0% | −1.3 |
| Claude Sonnet 5 | 96.8% | 98.4% | −1.6 |
| GPT-5.6 Terra | 92.5% | 96.0% | −3.5 |
| EuroLLM-9B | 88.2% | 89.8% | −1.6 |
| GEITje-7B-ultra | 78.8% | 85.3% | −6.4 |
| ChocoLlama-8B | 69.2% | 59.5% | +9.7 |
| Gemma 4 12B | 63.3% | 63.0% | +0.3 |

Computed on all 493 pairs (public plus held-out), clean subset, first run. Only ChocoLlama's gap
survives Holm correction for seven models. ChocoLlama is the only model with Belgian training data
and the only one that scores *better* on Belgian Dutch.

## How it was built

1. **Word selection** from the Dutch Crowdsourcing Project norms: words known by ≥80% in their own
   country and ≥30 points less in the other. 584 Belgian, 497 Netherlands candidates.
2. **Pairing**: one-to-one matching on own-country familiarity (±3 points) and on the
   between-country difference (±5 points). 493 pairs.
3. **Correct answers**: drafted independently by Claude Opus 5 and Gemini. 1,018 of 1,081 agreed;
   the 63 disagreements were decided by the author (a native Flemish speaker); 11 uncertain
   Netherlands words were decided by a Netherlands-Dutch speaker, who rejected 4.
4. **Distractors**: meanings of other words in the set, with no shared content words with the
   correct answer, no resemblance to the target word, and comparable length.

Provenance of the correct answers in this public split: 762 drafted by Claude, 17 by Gemini, 4
written by the author, 5 by the Netherlands reviewer; 194 items carry an explicit human review.

## Limitations

- **Isolated word meaning only.** No context sentences, no syntax, no administrative language, no
  institutional knowledge, no spoken language.
- **Ceiling effect.** The strongest models score 97–100%, leaving little room to measure a
  difference; their gaps are lower bounds.
- **Correct answers are partly LLM-drafted**, and one of the drafting models (Claude) is among the
  evaluated models. An advantage for Claude cannot be ruled out. Use `drafted_by` to check.
- **No human baseline.** Model scores are not compared against native speakers answering the same
  questions.
- **Noise floor.** Repeated runs give 93–99% identical answers, so differences under 1–2 points can
  be run-to-run variation.
- **`A1a-overlap` items are easier**; exclude them for the headline.
- **Single author** for the Belgian side; no second Flemish reviewer has checked a sample yet.

## Licence and citation

CC BY 4.0.

```bibtex
@misc{flembench2026,
  title  = {flembench: a paired benchmark for Belgian vs Netherlands Dutch vocabulary in LLMs},
  author = {Gilles (@GillesVdSpiegel)},
  year   = {2026},
  url    = {https://github.com/GillesVdSpiegel/flemish-llm-benchmark}
}
```

Word selection derives from the prevalence norms of Brysbaert, Keuleers, Mandera & Stevens (2019),
*Recognition Times for 54 Thousand Dutch Words*, Psychologica Belgica 59(1), licensed CC BY-NC 4.0.
Those norms are **not redistributed** in this dataset; only words, questions and our own meanings
are included.
