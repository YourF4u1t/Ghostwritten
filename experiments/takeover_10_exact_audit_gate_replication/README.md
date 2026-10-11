# Takeover 10 — Exact replication of the audit gate

## Motivation

Takeover 07 reported GLM-5.2 strategy adoption of 7/12 after a signed self audit
and 0/12 after an otherwise identical other audit. Two subsequent designs with
perfect declarative source control did not reproduce a self advantage. Before
developing any more mechanism stories around the original result, it needs a
direct replication without prompt or implementation changes.

## Pre-registered design

- Reuse `takeover_07_restored_behavior_window.run_one` directly rather than
  copying or editing its prompts, tool, seed construction, environment, grader,
  temperature, or turn order.
- Model: GLM-5.2, with the exact same authentic Qwen3.5-4B Experiment G donor.
- Conditions: `native_no_audit`, `native_audit_self`, and
  `native_audit_other`.
- n=24 per condition; 72 total attempts; concurrency two.
- The only study-level changes are restricting execution to GLM and increasing
  n from 12 to 24.

## Outcomes and decision rule

The primary confirmatory comparison is exact four-step procedure in
audit-self versus audit-other using a two-sided Fisher exact test. Goodwill,
procedure score, and the no-audit cell are diagnostics. Actor plus own-history
labels and tool calls must be congruent for the manipulation to count.

- If the replication independently shows a significant self advantage with
  clean manipulation, retain the effect as a narrow, prompt-specific phenomenon
  and then test free evidence elaboration as a moderator.
- If the direction is weak or non-significant despite a clean manipulation and
  a nonzero no-audit window, classify Takeover 07 as non-replicated and freeze
  the actor-gating branch.
- The original and replication may be pooled only as an exploratory estimate;
  pooling cannot rescue a failed confirmatory replication.

## Completed results

- All 72 attempts completed without API, runner, parsing, or sample failures;
  every cell has the planned n=24.
- Tool use and declarative source interpretation were perfect:
  audit-self was current actor plus `OWN_HISTORY: YES` in 24/24, and audit-other
  was other actor plus `OWN_HISTORY: NO` in 24/24.
- The primary effect replicated:
  - audit-self exact procedure and goodwill: 10/24 (41.7%; Wilson 95% CI
    24.5%--61.2%);
  - audit-other: 2/24 (8.3%; 2.3%--25.8%);
  - Fisher p=.0173; odds ratio 7.86.
- Native/no-audit was 7/24 (29.2%), confirming an open behavior window and
  closely matching the original 4/12 (33.3%).
- Neither replication cell differed significantly from its corresponding
  original cell: self 41.7% versus 58.3% (p=.483); other 8.3% versus 0%
  (p=.543).
- Exploratory pooling across original and replication gives self 17/36 versus
  other 2/36 (Fisher p=9.77e-5; OR=15.21). This pooled value is descriptive,
  not the confirmatory test.

## Interpretation and value

Takeover 07's actor contrast is independently reproduced under its exact
procedure and remains a **B-grade mechanism candidate**. The result is not a
generic response to actor labels: Takeover 08's inline evidence and Takeover
09's fixed-acknowledgment channels did not show the self advantage despite
perfect source judgments. The justified claim is narrower:

> Under a free-response provenance-audit sequence, changing the signed actor
> identity from current to other causally changes GLM-5.2's reuse of an
> authentic transplanted strategy, even though task, trace, evidence authority,
> turn distance, and source-recognition accuracy are held fixed.

This narrow result matters because it links autobiographical source integration
to downstream action rather than verbal memory claims alone. However, it is
still one recipient model, donor, task family, and audit wording. It cannot yet
support a general identity or defense claim.

The discrepancy with Takeover 09 identifies a concrete moderator candidate:
the original procedure permits a free evidence-integration response immediately
after the tool result, whereas Takeover 09 forces a neutral fixed acknowledgment.
That moderator is post-hoc until tested in a single randomized factorial study.
