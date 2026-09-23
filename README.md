# flembench — does your LLM know Flemish?

**Do current LLMs perform measurably worse on Belgian Dutch (Flemish) than on Netherlands Dutch?**

For word meaning, the answer is: **hardly, and it depends on the training data.** Models score
about equally well on Belgian and Netherlands words of the same human difficulty. The clearest
effect is not the provider or the model size, but what went into training:

| Model | Belgian | Netherlands | Gap | 95% CI |
|---|---|---|---|---|
| **ChocoLlama-8B** (Belgian + NL training data) | 69.2% | 59.5% | **+9.7** | +3.2 … +15.8 |
| **GEITje-7B-ultra** (Netherlands-centric data) | 78.8% | 85.3% | **−6.4** | −11.8 … −1.3 |
| GPT-5.6 Terra | 92.5% | 96.0% | −3.5 | −7.0 … −0.3 |
| Claude Sonnet 5 | 96.8% | 98.4% | −1.6 | −3.8 … +0.5 |
| EuroLLM-9B | 88.2% | 89.8% | −1.6 | −6.2 … +2.9 |
| Gemini 3.8 Flash | 98.7% | 100.0% | −1.3 | −2.7 … −0.3 |
| Gemma 4 12B | 63.3% | 63.0% | +0.3 | −6.7 … +7.0 |

A positive gap means better on Belgian Dutch. 373 matched pairs, first run per model; after Holm
correction for seven models only ChocoLlama is significant. Five of seven models score lower on
Belgian words, but each difference on its own stays within the noise once corrected. Full results and limitations:
**[docs/bevindingen.md](docs/bevindingen.md)** (in Dutch).

## Why this exists

Dutch-language LLM evaluation (EuroEval, DUMB, the Amsterdam government benchmark) does not
separate Belgian from Netherlands Dutch. Flemish organisations deploying these tools have no
evidence either way. This benchmark answers the question for one measurable slice: **vocabulary**.

## Method in one page

The core problem: if Belgian questions are simply harder, a lower score proves nothing. So every
Belgian word is **paired with a Netherlands word that is equally well known in its own country**,
using the prevalence norms of the Dutch Crowdsourcing Project (Brysbaert et al. 2019), which
measured word knowledge separately for Belgium and the Netherlands.

- **493 pairs**, matched to a mean difference of **0.6 percentage points** in own-country
  familiarity.
- One multiple-choice question per word, identical template for both varieties:

  > Wat betekent het woord "zwalpen" zoals het in België gebruikt wordt?
  > A. klotsen  B. treuzelen  C. een beetje dik  D. dorpsplein

- The correct answer sits in the **same position** for both members of a pair, so a model's
  preference for a given letter cannot create a gap.
- Distractors are meanings of other words, with no shared content words and comparable length.
- **120 pairs whose meaning resembles the word itself** (*bakkerin* → *bakkersvrouw*) are reported
  separately; the headline uses the 373 clean pairs.
- **20% of pairs are held out** in a private repository, so contamination can be checked later.

Correct answers were drafted independently by two models (Claude Opus 5, Gemini) and checked: 1,018
of 1,081 agreed, the 63 disagreements were resolved by the author, and 11 uncertain Netherlands
words were decided by a Netherlands-Dutch speaker. Every item records where its gold answer came
from.

Design rationale and trade-offs: **[docs/decisions/0001-pairing.md](docs/decisions/0001-pairing.md)**.

## Reproduce

```bash
uv sync --all-extras
cp .env.example .env            # add API keys
uv run flembench generate-a1    # build questions from the word pairs
uv run flembench estimate claude-sonnet-5
uv run flembench run claude-sonnet-5 --budget 1
uv run flembench rescore        # re-scores everything from cache, no API calls
uv run python scripts/error_analysis.py
```

Every model response is cached in `runs/cache/`, so re-scoring never costs money. Local models run
through Ollama; `scripts/setup_local_models.py` pins their weights by SHA-256 and
`scripts/check_local_tokenization.py` verifies each one receives exactly the token sequence its
original tokenizer would produce.

Total API cost of the full study, including repeat runs: **$1.25 (about €1.15)**.

## What this does not show

Summarised (full list in the Dutch write-up): only isolated word meaning, no context, no
administrative language and no institutional knowledge; a ceiling effect for the strongest models
(Claude at 97–98%); gold answers partly drafted by models, one of which is under test; no human
baseline; and a run-to-run noise floor of 1–2 points.

## Licences

Code MIT (`LICENSE`), dataset CC BY 4.0 (`LICENSE-DATA.md`). Word selection derives from norms
licensed CC BY-NC 4.0, which are not redistributed here.
