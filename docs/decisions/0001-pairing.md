# 1. Mirrored word pairs matched on human prevalence

**Status:** accepted, used in v1 · 2026-09-22

## The problem

To claim "a model is worse at Belgian Dutch", the Belgian and Netherlands questions have to be
equally hard. Otherwise a lower Belgian score just means the Belgian questions were harder, and
the whole result collapses under the first critical question an interviewer asks.

## Options considered

**A. Belgian word against its common-Dutch synonym** (*frigo* ↔ *koelkast*).
Rejected: the synonym is ordinary Dutch and trivially easy, so every model scores near 100% on
the Netherlands side. The comparison measures nothing.

**B. Mirrored pairs, matched by author judgement.** A Belgian-specific word against a
Netherlands-specific word that "feels" equally common. Rejected as the primary basis: the
matching rests entirely on one person's intuition, exactly the weak point that needs defending.

**C. Mirrored pairs, matched on measured human word knowledge.** Chosen. The Dutch Crowdsourcing
Project (Brysbaert et al. 2019) measured for 54,000 words how many Belgians and how many Dutch
speakers know each word. Each Belgian word is matched to a Netherlands word that is **as well
known in its own country** (within 3 points) and **as unknown in the other country** (within 5
points).

## Consequence

- The pairs are matched to a mean difference of **0.6 percentage points** in own-country
  familiarity, from published, citable data rather than intuition.
- Because human difficulty is equal by construction, a difference in model scores is a property of
  the model, not of the item list.
- 493 usable pairs, far more than hand-written items would ever have allowed.

## The trade-off

1. **Prevalence is recognition, not comprehension.** The norms asked "do you know this word?", not
   what it means. A word can be recognised without its meaning being known, so our matching is
   slightly coarser than the test we build on it.
2. **The norms date from around 2013.** Word familiarity shifts; the underlying data is over a
   decade old.
3. **Matching on familiarity says nothing about frequency in training data**, which is what
   actually drives model knowledge. That is the point, though: we hold *human* difficulty constant
   and let the model side vary.
4. **It only works for single words.** Administrative language, sentence structure and register
   cannot be matched this way and need a different design.
5. **CC BY-NC.** The norms cannot be republished with the dataset, so the values stay out of it and
   a script fetches them from OSF.

## What I would change next time

**Measure human performance on the items themselves, not just word familiarity.** Prevalence is a
proxy for difficulty; a small human baseline on the actual questions would be a direct measure and
would also show whether a Netherlands speaker really does worse on the Belgian items, which is the
strongest validity check available. That is planned for v1.1 and is the largest gap in v1.

A cheaper second improvement: match on **frequency in a Belgian and a Netherlands corpus** as well
as on prevalence, so exposure and familiarity are both held constant.
