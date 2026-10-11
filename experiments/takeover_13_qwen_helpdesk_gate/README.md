# Takeover 13 — Cross-model helpdesk adoption and provenance

## Motivation

GLM-5.2 perfectly retained the transplanted helpdesk workflow after correctly
classifying it as another agent's history. This study tests whether that
declarative/behavioral dissociation generalizes to Qwen3-8B, while avoiding a
same-family donor by generating one authentic GLM-5.2 trajectory.

## Pre-registered design

- One planned GLM-5.2 donor-generation attempt under the helpdesk reliability
  protocol. Failure or an incomplete donor stops the study without retry.
- Recipient: Qwen3-8B.
- Conditions: baseline, native/no-audit, native/audit-self, and
  native/audit-other; n=20 each, 80 subject attempts total.
- Same held-out employee, ticket, tools, source probe, free-response provenance
  audit, signed record, and behavioral outcomes as Takeovers 11--12.
- Baseline has no donor history; every native cell gets the same authentic
  cross-family history. All cells expose the same tool schema.

## Hierarchical outcomes and decision rule

The primary behavioral outcome is the 72-hour monitoring watch. Exact procedure
and required VPN reset are diagnostics.

1. First test native/no-audit versus baseline. If no native window exists, the
   actor comparison is not interpreted.
2. If the window exists and both source manipulations are understood, test
   audit-self versus audit-other.
3. Compare each audited cell with no-audit to diagnose the audit-distance floor
   seen for Qwen in the retail task.

Persistence in audit-other with correct `OWN_HISTORY: NO` supports a cross-model
declarative/behavioral dissociation. A self advantage supports a model-general
actor gate. If both audited cells collapse, the actor result is inconclusive and
classified as an audit-distance boundary.

## Completed results

- The single planned GLM-5.2 donor attempt succeeded with the exact four-step
  procedure. All 80 Qwen3-8B subject episodes completed without API, runner, or
  sample failures; every cell has n=20.
- The native history opened two clean behavioral windows while required repair
  stayed complete:
  - 72-hour monitoring/exact procedure: baseline 0/20 versus native/no-audit
    13/20 (Fisher p=1.29e-5);
  - device-profile lookup: 0/20 versus 20/20;
  - VPN reset: 20/20 in both.
- The audit did not recreate the retail distance floor. Monitoring was 11/20 in
  audit-self and 11/20 in audit-other, compared with 13/20 no-audit (each audit
  versus no-audit p=.748).
- Qwen correctly reported the final actor in every audited trial: self was
  current actor 20/20 and other was other actor 20/20. Self also yielded
  `OWN_HISTORY: YES` 20/20.
- In the other-actor cell, however, Qwen returned `OWN_HISTORY: NO` only 9/20
  and contradicted the actor field with `OWN_HISTORY: YES` in 11/20. The planned
  joint manipulation therefore failed for that cell.
- Exploratorily, monitoring persisted in 5/9 clean other/NO trials and 6/11
  inconsistent other/YES trials. These selected subsets are nearly identical
  and cannot be treated as a randomized actor-gate test.

## Interpretation and value

The helpdesk history-adoption effect generalizes across both donor and recipient
model families: a real GLM trajectory changes Qwen's tool behavior without
changing required task completion. This is **B-grade cross-model support** for
behavioral transplantation and independently shows that individual procedure
components can move from 0% to 100% or 65%.

The actor-gating hypothesis is not cleanly tested because Qwen fails to map a
correct other-actor record onto autobiographical non-ownership in more than
half the trials. That failure is itself a **B-grade representation boundary**:
Qwen can state who acted while simultaneously claiming that actor's trace as
its own history. It echoes the earlier Qwen inconsistencies and should be
treated as a stable separation between event-source identification and memory
ownership, not as random parser error.

The equal 11/20 behavior rates and the exploratory 5/9 residual among clean
`NO` judgments suggest behavioral persistence, but they are only **C-grade**
for dissociation because ownership was not successfully randomized across the
full other cell.

Decision: retain the cross-model adoption and actor-versus-ownership separation;
do not claim a valid Qwen actor-gate null. A future Qwen study should manipulate
ownership semantics directly rather than assuming an actor ID will entail
non-ownership.
