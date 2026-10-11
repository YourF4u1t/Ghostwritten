# Validation — Takeover 06

## Verdict

**INCONCLUSIVE for the primary question.** The behavioral adoption window
collapsed, Qwen3-8B's attribution labels were internally inconsistent, and one
demo cell fell below the minimum sample threshold. Preserve the study as a
transparent method audit and two C-grade exploratory leads.

## Execution and integrity

- 120 attempted episodes; 114 valid and six unretried HTTP 429 failures.
- Valid Qwen3-8B cells: baseline 12, native/no-audit 12, audit-self 11,
  audit-other 10, demo/audit-other 9.
- Every GLM-5.2 cell retained n=12.
- All 66 valid audited episodes called the provenance tool and produced the
  requested labels.
- No runner errors, manual exclusions, or selective retries.
- The donor loader verified that every authentic trace contains all four
  procedure tools and at least one tool-call reference.

## Primary statistical result

The pre-specified exact-procedure contrast was:

- GLM-5.2: audit-self 3/12 versus audit-other 0/12, Fisher p=.217,
  Holm-adjusted p=.435.
- Qwen3-8B: audit-self 1/11 versus audit-other 0/10, Fisher p=1,
  Holm-adjusted p=1.

These contrasts are not interpretable as evidence against behavioral residue,
because native/no-audit did not exceed baseline: Qwen3-8B 0/12 versus 0/12 and
GLM-5.2 1/12 versus 0/12. The study lacked the adoption window required by its
own decision rule.

## Manipulation audit

GLM-5.2 cleanly followed the signed actor record in every valid audit trial and
used congruent history-use labels. Qwen3-8B did not: all 21 valid native audit
trials said `EXTERNAL_REFERENCE`, while 18 also emitted `FINAL_OWNERSHIP: SELF`.
The accompanying text typically described the named worker as another agent.
Thus its SELF label cannot be used as a clean declarative-state variable here.

## Prompt contamination

Two additions relative to Experiment G likely closed the window:

1. the system prompt explicitly described the prior context as transplanted;
2. the held-out request began "handle a new customer independently."

The audit probe also named a "damaged-item workflow," which can reactivate the
very procedural schema measured downstream. Qwen3-8B's redundant `get_user`
step increased from 0/12 without audit to 21/21 across the two native audit
conditions, independently of returned actor. This is intriguing but cannot be
separated from direct semantic priming in the current design.

## 11/11 statistical fallacy scan

1. **Tiny samples / power:** n=10--12 for most cells and n=9 for Qwen demo;
   modest actor effects are underpowered.
2. **Multiple comparisons:** the two planned primary tests use Holm correction;
   ritual and demo observations are explicitly exploratory.
3. **Pseudoreplication:** stochastic repeats share one donor per model and one
   held-out task.
4. **Non-independence / leakage:** authentic histories overlap the same task
   family; cross-domain behavior is not claimed.
5. **Selective reporting:** nulls, API failures, label contradictions, floor
   effects, and contamination are all reported.
6. **Post-hoc subgrouping:** final-OTHER diagnostics were pre-specified; the
   ritual reactivation observation is marked post-hoc.
7. **Dichotomization:** exact sequence and component steps are both reported,
   together with continuous procedure score.
8. **Mean-only reporting:** exact counts, Wilson intervals, and cell means are
   available from the analysis script.
9. **Correlation as causation:** no actor-gating or reactivation cause is claimed
   under the contaminated prompts.
10. **Null equals no effect:** primary nulls are called inconclusive because the
    manipulation window was absent.
11. **Measurement / floor-ceiling effects:** exact procedure is near floor in
    native cells; GLM ritual is at baseline ceiling; Qwen labels are incongruent.

## Decision

1. Do not promote declarative-behavior dissociation from this run.
2. Restore the original G wording, remove "transplanted" and "independently,"
   and use explicit actor IDs plus a binary own-history judgment.
3. If the behavior window reopens, test audit-self versus audit-other again;
   otherwise freeze the branch.
