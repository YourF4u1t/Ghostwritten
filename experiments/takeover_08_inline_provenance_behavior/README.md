# Takeover 08 — Inline provenance and downstream behavior

## Motivation

Takeover 07 restored strong native behavioral adoption, but any three-turn
interactive audit suppressed the complete procedure regardless of whether the
audit named self, other, or an unresolved actor. This is confounded with known
history-distance decay. A practical provenance intervention should therefore be
tested without adding conversational turns before action.

## Research question

When signed provenance metadata is placed inline with the next task, does actor
identity gate adoption of a role-native transplanted procedure while preserving
the behavioral window?

## Design

- Same cross-family authentic Experiment G donors and umbrella task.
- Models: Qwen3-8B and GLM-5.2; n=12 per condition.
- Conditions:
  - `baseline`;
  - `native_no_metadata`;
  - `native_inline_self`;
  - `native_inline_other`;
  - `native_inline_unknown`.
- Inline conditions prepend a fixed-format signed provenance block to the same
  user message as the held-out customer request. No audit turn or assistant
  response intervenes between metadata and action.
- Metadata blocks are identical except `all_events_performed_by` and
  `actor_resolution`.
- Actor-ID and own-history judgments are collected only after the main action,
  so measurement cannot change the behavior being measured.
- Total planned attempts: 120; concurrency two.

## Pre-specified outcomes and decision rules

Primary behavior is exact four-step procedure; secondary outcomes are $5
goodwill credit, redundant `get_user`, and procedure score. Primary actor
contrast is inline-self versus inline-other exact-procedure rate within model,
with Holm correction. Inline-unknown diagnoses whether uncertainty is
intermediate.

The window is valid if native/no-metadata exceeds baseline and inline-self
retains nontrivial adoption. A lower inline-other rate with correct post-action
source judgment supports attribution-gated behavior. Comparable self and other
rates support declarative/behavioral dissociation. If every metadata block
suppresses behavior, inline metadata itself is a salience or distance defense,
and actor-specific conclusions are not licensed.

## Completed results

- All 120 planned episodes completed successfully, with n=12 in every cell and
  no API, runner, or parsing failures.
- The behavioral window was open for GLM-5.2: native/no-metadata produced the
  complete procedure in 6/12 trials versus 0/12 at baseline (Fisher p=.0137;
  Holm-adjusted p=.0275). Qwen3-8B was directionally higher at 3/12 versus
  0/12, but imprecise (p=.217).
- The pre-specified inline actor contrast did **not** reproduce Takeover 07's
  GLM gate:
  - inline-self: 4/12 complete procedure and goodwill;
  - inline-other: 3/12;
  - Fisher p=1.0, Holm-adjusted p=1.0.
- This GLM null is interpretable rather than a manipulation failure. Post-action
  judgments were perfectly congruent in both cells: self metadata yielded
  current actor plus `OWN_HISTORY: YES` in 12/12, while other metadata yielded
  other actor plus `OWN_HISTORY: NO` in 12/12.
- For Qwen3-8B, inline-self was 0/12 and inline-other 2/12 (p=.478). The model
  did not parse the other-source semantics coherently: it reported the current
  actor in 10/12 but `OWN_HISTORY: NO` in 11/12. This cell cannot support an
  actor-gating interpretation.
- The unknown condition was not a valid uncertainty gradient. GLM adopted the
  complete procedure in 7/12 and returned `UNKNOWN` actor in 8/12, but still
  called the trace its own in 9/12. Qwen defaulted to current actor and own
  history in 12/12.
- Baseline post-action source answers are excluded from provenance inference:
  the question presupposed an earlier case history even though baseline had no
  donor trace.

## Interpretation and value

Takeover 08 supplies a **B-grade boundary/falsification result**. GLM can
perfectly separate declarative provenance while continuing to reuse a strategy
at comparable rates. Therefore Takeover 07's 7/12 versus 0/12 contrast should
not be generalized to "ownership labels gate strategy adoption." The effect is
conditional on the active audit interaction, evidence presentation channel,
or their induced retrieval/salience state.

This also rules out a simple practical claim that signed inline provenance is a
reliable behavioral defense: neither model showed a significant reduction for
other-source metadata relative to self-source metadata, and GLM still executed
the complete transplanted procedure in 3/12 other-source trials despite perfect
source correction.

Value grades:

- **B boundary:** declarative provenance and strategy reuse dissociate under
  passive inline evidence in GLM-5.2.
- **B revision:** Takeover 07 remains a real prompt-level causal contrast, but
  its mechanism is active-audit/channel-specific rather than source ownership
  alone.
- **C:** actor-unavailable metadata can coexist with self-ownership defaults;
  the condition failed as a calibrated uncertainty manipulation.
- **D:** universal claims that source correction gates adoption or that inline
  provenance is a sufficient defense.

The next experiment should directly isolate active provenance retrieval from
passive evidence presentation while matching turn distance and text position.
