# Project brief: Flemish-Dutch LLM benchmark

Kickoff prompt for a Claude Code session. Save it in the repo root as `BRIEF.md` and start with: "Read BRIEF.md and give me your plan."

## Purpose — read this first

This is a portfolio and CV project, not a commercial product. I am a developer in Antwerp moving into applied-AI consulting, AI enablement or solutions engineering. This benchmark is one of the main artifacts I will show recruiters and interviewers.

That changes what "good" means here:

* **Methodology is the product.** An interviewer will not care how many models I tested. They will ask how I know my items are valid, how I scored open-ended answers, and whether the differences I report are real or noise. Every design decision should be defensible under that questioning.
* **Finished beats ambitious.** A small, clean, reproducible benchmark with honest limitations beats a large one that never ships. Flag scope creep whenever you see it.
* **Honest reporting over impressive numbers.** Null results, unexpected results and limitations get written up as findings, not hidden.
* **Everything must be publishable.** Dataset, code and write-up will be public. That means licence-clean sources, no personal data, and reproducible runs.
* **Low cost.** Budget is a few euros of API spend in total.

## The research question

Do current LLMs perform measurably worse on Belgian Dutch (Flemish) than on Netherlands Dutch, and if so, in which kinds of tasks?

Most Dutch-language AI evaluation is built around Netherlands Dutch. Flemish businesses and public services deploying these tools have no clear answer to whether the tools understand their Dutch — vocabulary, administrative language, institutional context. This benchmark answers that for a defined, measurable slice.

The headline result should be a single comparable number per model: the **Flemish gap** — performance on Belgian-Dutch items minus performance on matched Netherlands-Dutch items — broken down by category, with confidence intervals.

## Core design: paired items

The key methodological choice. Wherever possible, each item exists as a matched pair: a Belgian-Dutch version and a Netherlands-Dutch version testing the same underlying skill at the same difficulty. Example: the same comprehension question over a gemeentelijke brief in Flemish administrative Dutch and an equivalent letter in Netherlands administrative Dutch.

Pairing isolates the variety effect from the task difficulty. Without it, a low score on Flemish items could simply mean the items were harder. Some categories (Belgian institutional knowledge) cannot be paired naturally — those are reported as a separate, unpaired track and do not feed the headline gap.

## Task categories (starting proposal — challenge it)

Prefer objectively scorable formats: multiple choice, exact match, normalised extraction. Open-ended generation is a separate, clearly labelled track.

1. **Lexicon in context.** Belgian-Dutch words and constructions whose meaning differs from or is absent in Netherlands Dutch (e.g. goesting, content, schoon meaning mooi, kot, subiet, frigo, gsm). Format: choose the meaning in context. Focus on Belgian Standard Dutch and common tussentaal. Deep regional dialect is excluded from the main set, or at most a small labelled hard subset.
2. **Administrative text comprehension.** Questions about official-style texts: letters from a gemeente, VDAB, FOD Financiën, a mutualiteit. Extraction and comprehension formats with gold answers. Paired with Netherlands equivalents.
3. **Belgian practical and institutional knowledge.** Government structure (federaal, gewest, gemeenschap, gemeente, OCMW, schepen), Belgian-specific terms (aanslagbiljet, rijksregisternummer, ziekenfonds), formats (postcodes, VAT rates, number and date conventions). Unpaired track. Avoid facts likely to change; record a "valid as of" date on each item.
4. **Variety identification.** Is a given sentence Belgian or Netherlands Dutch, and what marks it? Objectively scorable, cheap to build, and a useful diagnostic.
5. **Generation in register (separate track).** "Write this email as a Flemish municipality would." Scored with a rubric by an LLM judge, with judge–human agreement measured and reported on a human-scored subset. Keep this track small. If judge–human agreement is poor, report that and exclude the track from conclusions.

## Item quality rules — non-negotiable

* **Items are human-authored or human-verified.** I am a native Flemish speaker and I own the gold answers. You may draft candidate items to speed up authoring, but every item passes my review before it enters the dataset, and each item records its provenance (`human_written` / `llm_drafted_human_verified`). LLM-generated benchmark items evaluated by LLMs is a known methodological weakness; the provenance field lets the analysis check whether it biased results.
* **Second reviewer.** A second native Flemish speaker reviews a random subset. Report agreement. Items two native speakers disagree on are ambiguous and get dropped, not debated.
* **Original items.** Do not copy items from existing benchmarks — contamination risk, and licence risk.
* **Source licensing.** Any real source text must be licence-compatible with publishing (Flemish government material under the Modellicentie Gratis Hergebruik or similar open terms is a good source). Record source and licence per item. Anonymise any real letter completely.
* **No personal data.** No real names, addresses, national register numbers or case details.
* **Held-out split.** Keep a private held-out portion unpublished so future contamination can be checked.

## Item schema (starting proposal)

Each item records at least: `id`, `pair_id` (nullable), `variety` (be / nl), `category`, `subcategory`, `prompt`, `format` (mc / exact / extraction / generation), `choices` (if mc), `gold`, `accepted_variants`, `scoring_method`, `difficulty` (my rating), `source`, `licence`, `valid_as_of`, `provenance`, `author`, `reviewed_by`, `notes`.

Stored as versioned JSONL. Schema validated in CI.

## Baselines

* **Human baseline:** a handful of Flemish speakers on a subset. Without it, a model score has no reference point.
* **Netherlands-Dutch human contrast (if feasible):** one or two Netherlands Dutch speakers on the same subset. If they also score lower on Flemish items, that is an important finding about the items, not just the models.

## Models

Five to seven models covering at least: two or three major commercial APIs, at least one open-weight model runnable locally or through a free tier, and — if one is currently available with a usable licence — a Dutch-tuned open model. Research which Dutch-tuned models are currently available and licensed rather than assuming.

Run conditions: temperature 0 where supported, fixed prompts and system messages across models, exact model identifiers and run dates recorded, responses cached so re-scoring never re-queries. At least three runs on a subset to estimate run-to-run variance.

## Analysis

* Per-category accuracy per model per variety, with bootstrap confidence intervals.
* The Flemish gap per model, paired where pairs exist.
* Cost per model run, in euros.
* An error analysis section: read the wrong answers and categorise why they were wrong. This is often the most interesting part of the write-up and the part interviewers remember.
* State clearly what the benchmark does not show.

## Environment and constraints

* Python, Windows with PowerShell, GitHub CLI (`gh`) authenticated.
* This project does need API keys for several providers. Keep them in a `.env` file that is gitignored from the first commit, never in code or logs. Set a hard spending cap in every provider's console before the first run.
* Estimate the cost of a full run before executing it, and tell me.
* Tests must not hit the network: recorded responses as fixtures, CI green on every push.

## Prior work — check first

Before designing anything, survey existing Dutch-language evaluation work (EuroEval, formerly ScandEval, covers Dutch; check for others) and report specifically whether any of it separates Belgian from Netherlands Dutch. If something close already exists, tell me — the project should be positioned relative to it, not in ignorance of it.

## Build order

* **Phase 1 — design doc.** Research question, final categories, item schema, scoring per category, pairing strategy, model list, cost estimate. Then write ten pilot items per category and run them against two models. Pilots exist to find broken categories early; expect to cut or redesign at least one.
* **Phase 2 — harness.** Model adapters behind one interface, run orchestration, response caching, scoring per format, schema validation. Fully tested offline.
* **Phase 3 — dataset.** Author and review items. Target 150–250 validated items for v1, balanced across categories. Quality over quantity: 150 clean items beat 500 noisy ones.
* **Phase 4 — baselines.** Human baseline on a subset; LLM judge calibration for the generation track.
* **Phase 5 — runs and analysis.** Full runs, variance runs, confidence intervals, error analysis.
* **Phase 6 — publish.**
  * GitHub repo: code under MIT, dataset under CC BY 4.0.
  * Dataset on Hugging Face with a proper dataset card: intended use, known limitations, construction method, provenance breakdown.
  * A write-up in Dutch (this project doubles as my Dutch-language portfolio piece), plus an English README summary.
  * A short Dutch LinkedIn post with the headline result.

## Explicitly out of scope

* A hosted leaderboard website.
* Fine-tuning or training any model.
* Deep dialect coverage beyond a small labelled hard subset.
* Commercial use, licensing the dataset for sale, or productising.
* A workshop. I plan a Dutch-language AI workshop for Flemish SME staff later, and results may feed it, but it is not part of this project. Nothing to build for it now.

## Engineering standards

* README opens with the research question and the headline result, then methodology, then how to reproduce.
* One documented design decision with the trade-off and what I would change — the pairing strategy is the obvious candidate.
* Reproducible end to end: one command re-scores all cached results.
* Conventional commits, one feature per branch.

## How to work with me

Start by reading this back as a short plan: the phases, your proposed repo structure and dependencies, the prior-work survey, and any question where my answer changes your approach. No code until we agree on Phase 1.

Then work one phase at a time and stop at every phase boundary for review. Item authoring is mine — build the tooling that makes authoring and review fast (a simple review interface or CLI is worth it), but do not fill the dataset yourself.

If any part of this plan is methodologically weak, say so directly. That is the most useful thing you can do on this project.
