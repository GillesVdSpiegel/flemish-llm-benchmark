# Design document — Flemish-Dutch LLM benchmark (Phase 1)

Status: **draft for review** · 2026-09-21 · Owner: @GillesVdSpiegel

This document fixes the research question, the measurement design and the analysis plan
*before* any model is run on the full dataset. Committing it first is a lightweight form of
pre-registration: every analysis reported later is either listed here or explicitly labelled
exploratory.

---

## 1. Research question and hypotheses

**RQ.** Do current LLMs perform measurably worse on Belgian Dutch (BE) than on Netherlands
Dutch (NL), and if so, in which kinds of tasks?

| | Hypothesis | Measured by | Status |
|---|---|---|---|
| H1 | Models score lower on BE-specific *language* than on matched NL-specific language | **Language gap** (Track A) | Primary, headline |
| H2 | Models score lower on Belgian *institutional context* than on matched Dutch context | **Context gap** (Track B) | Primary, second number |
| H3 | The gap is larger for smaller and Dutch-tuned-on-NL models than for frontier models | Gaps compared across models | Secondary |
| — | Per-category gaps, error types, variety-identification bias, generation quality | Tracks C, D, error analysis | Exploratory |

**Why two gaps and not one.** A model that fails on *aanslagbiljet* may lack Flemish
vocabulary, or it may simply know little about a small bilingual country whose public
information is split between French and Dutch. These are different problems with different
remedies, so they are reported separately and never pooled.

## 2. Prior work and positioning

Survey (September 2026) found no LLM evaluation that separates Belgian from Netherlands Dutch:

- **EuroEval** — 27 Dutch datasets; none labels or reports variety. Some source data is
  Belgian (CoNLL-nl: *De Morgen*) but mixed in.
- **Samson et al. 2026, "From Values to Benchmarks"** — 31 LLMs for Dutch governmental use;
  Netherlands only. Closest public-sector analogue.
- **VarDial 2018 DFS** — Dutch-vs-Flemish subtitle *classification*; pre-LLM, data not
  redistributable. Prior art for Track C.
- **DIALECTBENCH (Faisal et al. 2024)** — variety gaps across 281 varieties; no BE-vs-NL LLM
  result.
- **bLLeQA (2026)** — Belgian legal QA, French vs Dutch — not BE vs NL Dutch.
- **Flemish sentiment (2025), FLAME** — Flemish-only data, no NL contrast.

**Positioning:** first paired BE/NL evaluation of LLMs, with difficulty matching grounded in
published human word-knowledge norms. To re-check against CLIN proceedings and Taalunie
publications before publication.

## 3. Tracks and categories

| Track | Category | Paired? | Feeds | Target size (v1) |
|---|---|---|---|---|
| **A — Language** | A1 Lexicon in context | yes, mirrored | Language gap | 60–80 pairs |
| | A2 Administrative comprehension | yes, parallel letters | Language gap | 20–30 pairs (pilot decides) |
| **B — Context** | B1 Institutional & practical knowledge | yes, functional analogue | Context gap | 30–40 pairs |
| | B2 Belgium-only structure | no | descriptive only | 10–15 items |
| **C — Diagnostic** | Variety identification | balanced classes | per-class recall | 40 items |
| **D — Generation** | Register writing | n/a | judge–human study | 10 prompts |
| (hard subset) | Regional dialect | mirrored if possible | excluded from headline | ≤ 15 items |

Total ≈ 260–340 items, of which ≈ 110–150 **pairs** drive the two primary numbers. This
deliberately departs from "balanced across categories": power is spent where the claims are
(see §8).

### A1 — Lexicon in context (mirrored pairs)

A pair is **one BE-specific word and one NL-specific word**, each in a short context sentence
in its own variety, with a 4-option "what does X mean here?" question. It is *not* a BE word
paired with its common-Dutch synonym (*frigo* ↔ *koelkast*) — the synonym is trivially easy.

Two subsets, reported separately inside A1:

- **A1a Recognition-based.** Candidates from the Dutch Crowdsourcing Project prevalence norms
  (Brysbaert, Keuleers, Mandera & Stevens 2019): words known by ≥ 80 % of speakers in their own
  country and ≥ 30 points less in the other. Pairs are matched one-to-one on **own-community
  prevalence** (± 3 pts) and **prevalence gap** (± 5 pts) by optimal assignment. By
  construction the *human* own-community difficulty is equal within a pair, so a model gap is
  a model effect. Feasibility (`scripts/lexicon_candidates.py`): 584 BE / 497 NL candidates,
  490 matched pairs before curation.
- **A1b Meaning shift.** Words known in both countries with a different or additional meaning
  in BE (*schoon* = mooi, *content*, *plezant*, *straks*, *direct*, *seffens*). Prevalence
  cannot flag these; sourced from Woordenlijst/Van Dale labels and author knowledge. Mirrored
  with NL meaning-shift words where possible; difficulty matched by author judgement only —
  a weaker match, stated as such.

**Curation rules** (applied by the author to every candidate, before matching):
1. Meaning is **opaque** — not inferable from word form by a Dutch reader (*inkom* is
   borderline; *recycleren* is rejected: recognition ≠ comprehension difficulty).
2. Not a brand name (*vlaflip*, *kliko*), not an abbreviation (*kmo*, *vmbo* → move to B1).
3. Current usage, not obsolete.
4. Register labelled: `standard` / `tussentaal` / `dialect`.
5. Context sentence is **uninformative** about the meaning — a model must know the word, not
   infer it. Checked by the second reviewer (see §9).
6. Distractors are plausible; for A1b one distractor is the *other variety's* meaning.

Matching is re-run **after** curation, so rejected words never break pairs.

### A2 — Administrative comprehension (parallel letters)

A BE letter (gemeente, VDAB, FOD Financiën, ziekenfonds) and an NL letter with the same
structure and purpose (gemeente, UWV, Belastingdienst, zorgverzekeraar), each with the same
question template. Letters are written by the author from scratch or adapted from
open-licensed templates (Modellicentie Gratis Hergebruik), fully fictional.

**Known risk — ceiling.** Plain extraction (dates, amounts) will be ~100 % in both varieties
and yield an uninformative zero gap. Questions must hinge on **variety-specific meaning**
inside the letter: what an *aanslagbiljet* obliges you to do, what *binnen de maand* means as a
deadline, whom *de schepen van ...* refers to. The pilot decides whether A2 survives; if both
pilot models score ≥ 95 % on both sides, A2 is cut or folded into A1/B1.

### B1 — Institutional knowledge (functional-analogue pairs)

Each BE item is paired with an NL item about the institution that fills the same role,
asked in the same form:

| BE | NL |
|---|---|
| rijksregisternummer — digits, check | BSN — digits, elfproef |
| schepen | wethouder |
| benoeming burgemeester | Kroonbenoeming |
| provinciegouverneur | Commissaris van de Koning |
| ziekenfonds, remgeld | zorgverzekeraar, eigen risico |
| VDAB / RVA | UWV |
| Groeipakket | kinderbijslag (SVB) |
| ondernemingsnummer (KBO) | KvK-nummer |
| postcode 4 cijfers | postcode 4 cijfers + 2 letters |

Difficulty matching has no norms to lean on; it is checked empirically by the human baseline
(Flemish participants on BE items, Dutch participants on NL items should score similarly;
pairs where they don't are flagged). Every item carries `valid_as_of`.

### B2 — Belgium-only structure (unpaired)

Gewesten vs gemeenschappen, community competences, language-border municipalities. No NL
counterpart exists; reported descriptively. The asymmetry itself — Belgian state structure is
harder — is a sentence in the write-up, not a confound to hide.

### C — Variety identification (diagnostic)

Sentence → "Belgisch-Nederlands of Nederlands-Nederlands?" plus "which word or construction
shows it?" Balanced classes; **graded marker density** (exactly one marker vs several) so
caricatured sentences don't make it trivial. Reported as per-class recall and a bias score
(does the model default to NL?). Not part of either gap.

### D — Generation in register

10 prompts ("schrijf deze brief zoals een Vlaamse gemeente dat zou doen"), all models. Rubric
(1–5) on three dimensions: register appropriateness, correct Belgian terminology/institutions,
naturalness for a Flemish reader. Scored by:

1. **The author**, blind (shuffled, model names hidden) — all ≈ 70 outputs.
2. **The second reviewer**, blind — a subset of 30, giving the human–human agreement ceiling.
3. **Two LLM judges from different providers.**

Reported: judge–human agreement (weighted κ, Spearman) *relative to* human–human agreement,
per generating model (judge self-preference check). If judge agreement is well below the
human ceiling, that is the finding and the judge is not used for conclusions.

## 4. Item schema

Stored as JSONL, one item per line, validated by a pydantic model / JSON Schema in CI.
Authored as YAML (one file per pair) and compiled.

| Field | Type | Notes |
|---|---|---|
| `id` | str | `a1-0001-be` |
| `schema_version` | str | semver |
| `pair_id` | str \| null | shared by both members |
| `variety` | `be` \| `nl` | |
| `track`, `category`, `subcategory` | str | `A`, `A1`, `A1a` |
| `register` | `standard` \| `tussentaal` \| `dialect` | |
| `marker` | str | the word/construction under test |
| `prompt` | str | item text in its variety; instruction wrapper is separate |
| `format` | `mc` \| `exact` \| `extraction` \| `generation` | |
| `choices` | list[str] \| null | |
| `gold` | str | |
| `accepted_variants` | list[str] | |
| `scoring_method` | str | named scorer, e.g. `mc_letter`, `norm_exact` |
| `difficulty` | 1–5 | author rating |
| `match_basis` | `dcp_prevalence` \| `functional_analogue` \| `author_judgement` \| null | how the pair was matched |
| `lexical_source` | str \| null | e.g. `Woordenlijst (BE)`, `DCP norms` |
| `source`, `licence` | str | for any real text used |
| `valid_as_of` | date \| null | required for B |
| `provenance` | `human_written` \| `llm_drafted_human_verified` | |
| `drafted_by` | str \| null | model ID if LLM-drafted |
| `author`, `reviewed_by` | str | |
| `second_review` | object \| null | blind answer, agree flag |
| `split` | `public` \| `heldout` | whole pairs are held out together |
| `notes` | str | |

**Licence boundary.** DCP prevalence values are CC BY-NC 4.0. They are **not** stored in
items; the analysis script joins them from the original download. The published dataset
(CC BY 4.0) contains only words, author decisions and `match_basis`.

## 5. Scoring

| Format | Scorer | Details |
|---|---|---|
| `mc` | `mc_letter` | Model must answer with a letter. Strict regex on the final line; lenient fallback (first standalone A–D). Unparseable = wrong, **reported separately** per model. |
| `exact` | `norm_exact` | casefold, trim, collapse whitespace, strip final punctuation; match gold or any accepted variant. |
| `extraction` | `norm_extract` | as `norm_exact`, plus canonical numbers (`1.234,56` ≡ `1234.56`), dates (→ ISO) and postcodes. |
| `generation` | rubric | §3-D. |

**Choice order.** Shuffled with a fixed seed, but the gold position is **identical for both
members of a pair** and balanced across pairs, so position bias cannot create a gap.

## 6. Prompting and run conditions

- One system message and one instruction wrapper per format, in **neutral Standard Dutch**,
  identical for BE and NL items and across models.
- Zero-shot. No chain-of-thought requested. Answer format stated explicitly.
- Lowest reasoning and sampling variance each API allows. This is **not uniform across
  providers**, and the write-up says so (checked 2026-09-21; settings in `config/models.yaml`):

  | Model | Temperature | Reasoning |
  |---|---|---|
  | claude-sonnet-5 | not supported by the API | thinking disabled |
  | gpt-5.6-terra | not set | effort `none` |
  | gemini-3.8-flash | 0 | `MINIMAL` (cannot be fully disabled) |
  | local (Ollama) | 0, fixed seed | none |

  Reasoning tokens are logged per call, so any residual reasoning is visible in the data.
  A reasoning-on run is an optional exploratory contrast.
- Recorded per call: exact model ID, provider, parameters, date, request hash, raw response,
  usage, cost. Cache key = hash(model ID, parameters, full prompt). Re-scoring never
  re-queries.
- Variance: 3 repeats on a stratified 60-item subset per model.

## 7. Models

| Model | Access | Licence | Why |
|---|---|---|---|
| `gpt-5.6-terra` | OpenAI API | proprietary | most-used provider in Flemish business |
| `claude-sonnet-5` | Anthropic API | proprietary | major provider |
| `gemini-3.8-flash` | Gemini API (paid tier) | proprietary | major provider; paid tier so items are not used for training |
| EuroLLM-9B-Instruct | local, Ollama, Q8 | Apache 2.0 | European open model |
| GEITje-7B-ultra | local, Q8 | CC BY-NC 4.0 | Dutch-tuned, NL-centric data |
| ChocoLlama-8B-instruct | local, Q8 | Llama 3 + NC data | Dutch-tuned, **includes Belgian data** |
| one current general open model ≤ 12B (Gemma/Qwen) | local, Q8 | open | open-weight reference |

Optional, subset only: one frontier model (`claude-opus-5` or `gpt-5.6-sol`) to test H3 at
the top end. Local models run on an RTX 5070 (12 GB); quantisation level is recorded and
listed as a limitation. Final versions of the open models are fixed at the start of Phase 5.

## 8. Analysis plan

**Primary estimate.** For each model and each paired track: gap = mean over pairs of
(score_BE − score_NL). 95 % CI by bootstrap **over pairs** (10 000 resamples); exact McNemar
test for H1/H2, Holm-corrected across models. Negative gap = worse on Belgian Dutch.

**Power.** Half-width of the 95 % CI on a paired gap, as a function of the share of discordant
pairs:

| pairs | 10 % discordant | 20 % discordant |
|---|---|---|
| 25 | ± 12 pts | ± 18 pts |
| 50 | ± 9 pts | ± 12 pts |
| 100 | ± 6 pts | ± 9 pts |
| 150 | ± 5 pts | ± 7 pts |

Hence ~100 pairs pooled in Track A for the headline, and per-category gaps labelled
exploratory.

**Also reported:** per-category accuracy per model per variety with bootstrap CIs; cost per
full run in euros; run-to-run variance; gap split by `provenance` (did LLM drafting bias
items?); gap split by `register`; human baselines alongside model scores.

**Error analysis.** Every wrong answer on Track A and B is read and coded (e.g. *NL meaning
substituted*, *literal/compositional reading*, *confused with French*, *hallucinated
institution*, *format failure*). Codebook fixed after the pilot.

## 9. Validity checks

- **Second reviewer, blind.** Answers a random 30 % of items without seeing gold. Items where
  their answer ≠ gold are dropped (not debated). Report raw agreement and Cohen's κ. They also
  flag A1 context sentences that give away the meaning.
- **Human baselines.** 4–6 Flemish and 2–3 Dutch participants on a ~60-item subset. Prediction
  for A1: a double dissociation (each group worse on the other variety's items). If Dutch
  participants score *as well as* Flemish ones on BE items, the items are too easy or too
  transparent — a finding about the items. Expected asymmetry: Flemings know more
  Netherlandisms than the reverse (media exposure).
- **Contamination.** 20 % held out (whole pairs, stratified by category), stored only in the
  private `flemish-llm-benchmark-heldout` repo. All models are evaluated on it; it is never
  published. Public-vs-held-out score difference is reported.
- **Gold on the NL side.** The principal author is Flemish, so golds for Netherlands-specific
  words and Dutch institutions are verified by a Netherlands-Dutch speaker, the mirror image of
  the second reviewer. Curation code `u` routes words the author does not know to that person.
- **Author bias.** A single Antwerp-based author may skew tussentaal towards Brabantic. The
  second reviewer ideally comes from another province; `register` and the region of each
  marker are recorded where relevant.

## 10. Cost estimate

Assumptions: ~300 items, ~400 input tokens/item average incl. wrapper (A2 letters longer),
~20 output tokens/item with reasoning minimal; Dutch tokenises less efficiently than English,
so ×2 safety factor. Prices from provider pages, 2026-09-21 (USD ≈ EUR at this precision).

| Model | $/M in | $/M out | Full run (×2 buffer) |
|---|---|---|---|
| gpt-5.6-terra | 2.00 | 12.00 | ≈ $0.60 |
| claude-sonnet-5 | 2.00 | 10.00 | ≈ $0.60 |
| gemini-3.8-flash | 0.75 | 3.75 | ≈ $0.20 |
| local models | 0 | 0 | electricity |

Whole project: pilot + 1 full run + variance runs (~1 extra full-run equivalent) + generation
track + 2 judges ≈ **€3–4**. With reasoning left on (~500 hidden tokens/item, ≈ $4–8 per
full run of the three API models) it rises to **€8–15** — hence the minimal-reasoning default. An optional frontier subset adds ≈ €1–2. Batch
APIs (−50 %) are available but not needed at this budget. The exact figure is recomputed
before every run and reported to the author.

## 11. Pilot (end of Phase 1)

| | Items |
|---|---|
| A1 | 10 pairs (A1a from curated candidates) |
| A2 | 5 pairs |
| B1 | 10 pairs |
| C | 10 items |
| D | 3 prompts |

Run on **two models**: `claude-sonnet-5` (API adapter) and EuroLLM-9B (local adapter), so
both adapter types are exercised. Cost < €0.10.

**Kill/redesign criteria per category:** both models ≥ 95 % on both varieties (ceiling);
both ≤ chance (floor/broken format); > 5 % unparseable answers; the author finds > 2 of 10
golds contestable on re-read. Expect at least one category to be cut or redesigned.

## 12. Known limitations (stated up front)

- Prevalence = self-reported **recognition** (2013 data collection), not meaning knowledge.
- A1b and B1 are matched by judgement, not norms.
- One principal author; human baselines are small convenience samples.
- Local models are quantised.
- The benchmark measures *written, standard-to-tussentaal* Dutch. It says nothing about
  speech, deep dialect, or French-language Belgium.
- A positive result says models are worse on these items — not on "Flemish" in general.

## 13. Decisions still open

1. Package manager: `uv` (faster, lockfile) vs plain `venv` + `pip-tools`. Recommendation:
   `uv`, a one-time user install.
2. Exact open general model and GGUF quantisation — fixed at the start of Phase 5.
3. Whether the optional frontier-model subset is run.
