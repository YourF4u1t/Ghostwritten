# Validation — Takeover 05

## Verdict

**PASS as a held-out null/boundary result.** The unguarded identity-binding
candidate did not replicate, with adequate primary sample sizes and a neutral
prompt matched to Takeover 03's logic. This result should narrow the claim, not
be hidden or converted into a new universal defense claim.

## Execution and integrity

- 96 planned attempts; 95 valid and one unretried HTTP 429 in Qwen3-8B demo.
- Primary valid cell sizes: native n=36 and demo n=35, both above the planned
  minimum of 30.
- Comparator cells each retained n=12.
- 95/95 valid episodes called the intended tool and produced every requested
  label.
- No runner errors, parse failures, partial records, or selective retries.
- Concurrency was reduced from six to four; only one rate-limit failure occurred.
- The runner reused the previously audited donor loader, demo renderer, signed
  ledger record, and outcome parser while recording the study as Takeover 05.

## Primary result

Qwen3-8B post-evidence identity binding (`SELF` plus `AUTOBIOGRAPHICAL`):

- native: 0/36, Wilson 95% CI 0%--9.6%;
- demo: 0/35, Wilson 95% CI 0%--9.9%;
- two-sided Fisher p=1.

All 71 valid Qwen3-8B episodes ended with the semantically aligned pair
`OTHER/EXTERNAL_REFERENCE`. Qwen3.5-122B-A10B was aligned in 24/24.

## Boundary result

Qwen3-8B initially labeled native history `SELF` in 36/36 and the explicitly
external demo `SELF` in 35/35. Thus its demonstration-framing failure from
Takeovers 02--03 replicated under neutral wording. Crucially, that initial
source confusion did not persist after exact signed actor evidence.

Qwen3.5-122B-A10B showed the intended initial separation: native 12/12 `SELF`,
demo 0/12 `SELF`, followed by complete correction of native history. The result
therefore distinguishes initial ownership induction from resistance to later
provenance correction.

## 11/11 statistical fallacy scan

1. **Tiny samples / power:** primary n=36/35 bounds common failures below about
   10% by Wilson upper limits; rare failures remain possible.
2. **Multiple comparisons:** one primary Fisher test was pre-specified;
   comparator summaries are descriptive.
3. **Pseudoreplication:** samples are stochastic repeats of one trajectory, not
   95 independent tasks; the claim is a held-out prompt boundary.
4. **Non-independence / leakage:** both channels share one donor and task, which
   controls content but does not establish broad domain prevalence.
5. **Selective reporting:** the single API error, all zero outcomes, and the
   contradiction with Takeover 03 are reported.
6. **Post-hoc subgrouping:** primary model, channels, sample thresholds, and
   comparator were pre-specified.
7. **Dichotomization:** identity binding uses two concordant categorical labels;
   full ownership distributions are also reported.
8. **Mean-only reporting:** exact counts and Wilson intervals are supplied;
   raw responses remain available.
9. **Correlation as causation:** the held-out null constrains generalization but
   does not identify which changed task feature removed the earlier anomaly.
10. **Null equals no effect:** upper confidence bounds are stated, and the
    initial demo-framing effect remains visible despite the post-evidence null.
11. **Measurement / ceiling-floor effects:** final correction is at ceiling, so
    future work should use downstream behavior sensitive to residual influence.

## Decision

1. Do not promote cross-domain exact-event identity fusion.
2. Retain initial source confusion plus successful provenance correction as a
   B-grade boundary/defense result.
3. Stop adding ownership-label replications for now; test whether declarative
   correction actually removes downstream strategy adoption.
