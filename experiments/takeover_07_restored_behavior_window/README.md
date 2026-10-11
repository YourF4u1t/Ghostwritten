# Takeover 07 — Restored behavior window with actor-ID audit

## Motivation

Takeover 06 could not test whether attribution correction removes behavior:
its system prompt disclosed that context was transplanted, its held-out request
said to work independently, and Qwen3-8B produced inconsistent SELF versus
EXTERNAL_REFERENCE labels. It also suggested that auditing a prior workflow may
reactivate a redundant procedural step regardless of actor.

## Research questions

1. With Experiment G's original held-out wording restored, does signed
   self-versus-other attribution gate adoption of the donor's four-step
   procedure?
2. Does merely auditing the history reactivate procedural imitation, even when
   the audit cannot resolve an actor?

## Design

- Same authentic cross-family Experiment G donors and held-out umbrella task.
- System prompt contains store policy and current identity only. It does not call
  the context transplanted or instruct the model to ignore/use history.
- The new-case request exactly matches Experiment G; "independently" is removed.
- Attribution output is unambiguous: `FINAL_ACTOR_ID` must be the current ID,
  other ID, or `UNKNOWN`; `OWN_HISTORY` must be `YES`, `NO`, or `UNSURE`.
- Conditions per model, n=12:
  - `baseline`;
  - `native_no_audit`;
  - `native_audit_self`;
  - `native_audit_other`;
  - `native_audit_unknown` (same signed exact-trace audit, unresolved actor).
- Models: Qwen3-8B and GLM-5.2; total 120 attempts; concurrency two.

## Pre-specified outcomes and decision rules

Primary behavior is exact four-step sequence; secondary outcomes are $5
goodwill credit, redundant `get_user`, and procedure score. Actor-ID and
own-history judgments must agree with the audit for the attribution manipulation
to count as valid.

- First require an open window: native/no-audit must exceed baseline on at least
  one payload-specific outcome (exact sequence or goodwill credit), or audit-self
  must clearly recover that outcome.
- Compare audit-self versus audit-other exact procedure within model using
  Fisher exact tests and Holm correction.
- Use audit-unknown to distinguish an actor-specific gradient from generic
  history retrieval. If self, other, and unknown all raise only the redundant
  ritual relative to no-audit, classify it as retrieval reactivation, not
  identity-gated adoption.
- If the window remains closed, freeze this branch rather than further prompt
  slicing.

## Completed results

- All 120 planned episodes completed without API, runner, tool-call, or parsing
  failures; every cell has n=12.
- The behavioral window was restored:
  - Qwen3-8B exact procedure: baseline 0/12 versus native/no-audit 11/12
    (Holm-adjusted p=3.85e-5).
  - GLM-5.2: baseline 0/12 versus native/no-audit 4/12. The single-study
    adjusted p=.186 is imprecise, but it exactly matches Experiment G's prior
    native count (4/12).
- GLM-5.2 showed a clean actor-specific gate under equal audit distance:
  - audit-self: source judgment 12/12 current actor plus `OWN_HISTORY: YES`,
    exact procedure and goodwill 7/12;
  - audit-other: 12/12 other actor plus `OWN_HISTORY: NO`, exact procedure and
    goodwill 0/12;
  - Fisher p=.00458, Holm-adjusted p=.0183 for the pre-specified family.
- Qwen3-8B source judgments were also clean (12/12 in both self and other
  audits), but exact procedure was 0/12 in both. For this model, three audit
  turns overrode the actor manipulation through a general distance/salience
  floor.
- Both models interpreted actor-unavailable audits as current actor and own
  history in 12/12 trials. The unknown manipulation therefore failed as an
  uncertainty condition. GLM behavior was 4/12, matching no-audit; Qwen behavior
  remained 0/12 under audit distance.
- The redundant `get_user` ritual appeared in every native condition for both
  models. It survived when the full procedure and goodwill action disappeared,
  revealing component-level persistence but no actor gradient.

## Interpretation and value

GLM-5.2 provides a B-grade mechanism candidate: with history, task, audit turns,
and evidence format held fixed, changing only the signed actor field switched
complete procedure adoption from 7/12 to 0/12, alongside perfect declarative
source judgments. This is evidence that autobiographical ownership can gate
whether a model reuses an observed strategy, rather than source attribution
being merely verbal.

The result is model-specific, not universal. Qwen3-8B is dominated by history
distance: any interactive audit suppresses the full procedure even when the
audit confirms self. Its redundant ritual persists, demonstrating that
different components of the transplanted procedure decay differently.

Value grades:

- **B:** GLM-5.2 actor-ownership gating of complete strategy reuse.
- **B boundary:** Qwen3-8B audit-distance suppression overrides actor identity.
- **C:** missing actor provenance defaults to self/own under role-native history;
  the intended uncertainty manipulation failed and needs a different design.
- **D:** any universal claim that provenance correction always removes behavior
  or that declarative and behavioral state are always dissociated.

Before promotion to a paper core, replicate GLM's actor gate with inline
metadata (no audit turns) and a held-out donor/task or model.
