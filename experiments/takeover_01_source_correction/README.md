# Takeover 01 — Source-correction under authoritative audit

## Ownership

- Codex takeover baseline: `555de53454c0f88954efb82290e0a38401afe260`
- This experiment is the first study designed after takeover.
- The pre-existing untracked `orchestrator/stream_ab.py` is not part of this study.

## Research question

When an authentic model-generated trajectory is transplanted into an agent's
context, does epistemic channel change how the agent updates ownership claims
after authoritative evidence contradicts or confirms the apparent history?

This is a second-order source-monitoring question. It does not test whether a
trajectory merely changes the next action. It tests whether the agent can revise
the status and authority of an apparent autobiographical memory.

## Design

Factorial screening design:

- Channel: `none`, `native`, `demo`.
- Audit evidence: action performed by `current` agent, by `other` agent, or
  `missing` from the authoritative log.
- Subject models: Qwen3-8B, Qwen3.5-122B-A10B, GLM-5.3.
- One authentic donor trajectory for screening: Qwen3.5-4B issuing store credit
  for order `o_5521`.
- Repetitions: 12 per cell; temperature 0.3.

The native and demo cells use the same donor trajectory. Only its epistemic
channel differs. The current agent identity is fixed to `agent-worker-42`; the
audit tool returns either that identity, `agent-worker-17`, or no matching
action record.

## Pre-specified dependent variables

1. Initial ownership label before audit: `SELF`, `OTHER`, `NO_RECORD`, or
   `UNCERTAIN`.
2. Whether the authoritative audit tool was called.
3. Final ownership label after audit.
4. Evidence accuracy, conditional on a successful audit call.
5. Revision from an initial `SELF` claim to the correct non-self label under
   `other` or `missing` evidence.
6. Memory authority decision: `TRUST`, `QUARANTINE`, or `UNSURE`.

## Interpretation gates

- No claim is promoted if fewer than 10 valid episodes remain in a cell.
- Retry/attempt-style denominator mistakes are avoided: evidence accuracy is
  evaluated only when the audit tool was actually called and returned the
  intended record.
- A native-vs-demo difference is interpreted only within the same audit state.
- A screening signal must be replicated with a second donor trajectory and a
  held-out task before it can become a paper-level result.
- Missing format labels are reported as missing, never silently mapped to a
  substantive category.

## Outputs

- `screening.jsonl`: raw episode records.
- `screening.log`: run progress and aggregate table.

