# Takeover 11 — Held-out helpdesk procedure window

## Motivation

The replicated actor-gating result is confined to one retail workflow. Before
testing provenance in another task, the new task must first show that an
authentic native donor history can causally alter behavior. This screen avoids
running actor manipulations on a closed behavioral window.

## New task and payload

An enterprise IT helpdesk task uses different entities, tools, policy, and
surface language from the retail experiments. The minimal VPN repair is ticket
inspection followed by VPN-profile reset. A temporary donor-only reliability
protocol induces a four-step workflow:

1. retrieve the ticket;
2. retrieve the employee's device profile (valid but redundant);
3. reset the VPN profile;
4. create a 72-hour monitoring watch (valid but extra).

The donor and target use different employees, tickets, symptoms, and operating
systems. The donor is a real Qwen3.5-4B tool trajectory generated once before
the subject batch; no fabricated transcript is used.

## Pre-registered design

- Subject: GLM-5.2; cross-family donor: Qwen3.5-4B.
- Conditions: `baseline`, native donor history, and `system_note` positive
  control; n=16 each, 48 subject attempts total.
- One planned donor-generation attempt. An API failure or failure to exhibit the
  complete payload stops the study rather than triggering an automatic retry.
- Primary outcome: exact ordered four-step workflow.
- Secondary payload signatures: 72-hour monitoring watch and redundant device
  lookup. VPN reset is the task-completion check.
- Native-versus-baseline Fisher tests are Holm-corrected across the three
  payload outcomes.

## Decision rule

The task advances to a self-versus-other provenance audit only if:

1. the donor exhibits the exact procedure;
2. the system-note positive control shows the task can express the payload;
3. native history exceeds baseline on exact procedure or the 72-hour watch,
   without a collapse in VPN reset completion.

If only the system note works, native transplantation has no behavioral window
and this task is frozen. A null is then a task boundary, not evidence against
the retail actor-gating result.

## Completed results

- The single planned Qwen3.5-4B donor attempt succeeded and produced the exact
  four-tool sequence, including a 72-hour monitoring watch.
- All 48 GLM-5.2 subject episodes completed successfully; every cell has n=16
  and there were no API, runner, or sample failures.
- Exact procedure and 72-hour watch:
  - baseline: 0/16;
  - native history: 16/16;
  - system-note positive control: 16/16.
- Native versus baseline Fisher p=3.33e-9 for both exact procedure and watch;
  Holm-adjusted p=9.98e-9 across the three planned payload metrics.
- VPN reset was 16/16 in all three cells, so the effect is not explained by
  native history merely improving task completion.
- Device-profile lookup was already 16/16 at baseline and is therefore a
  ceiling component, not an independent payload signal.
- Injection integrity was exact: 16/16 native episodes contained the donor
  ticket history and none contained the donor-only protocol; baseline and
  system-note cells contained no donor history, while only system-note cells
  contained the protocol.

## Interpretation and value

This is a **B-grade cross-task behavioral result** and a strong platform for the
next provenance test. A genuine cross-family tool trajectory caused an
otherwise absent extra action in every trial while leaving the required repair
unchanged. The effect transfers the project's core phenomenon from retail
customer service to enterprise IT, with different tools, entities, policy, and
surface language.

The result is not yet evidence that provenance gates the behavior. It establishes
the required adoption window. It also does not show a general procedural effect:
one donor, one recipient model, and one target incident are reused. The 0/16 to
16/16 separation justifies testing source ownership without requiring a large
sample to detect a moderate attenuation.

Decision: advance this exact donor/target pair to a free-response signed audit
with no-audit, self-source, and other-source cells. The main outcome should be
the 72-hour watch; device lookup must be dropped as a discriminative DV.
