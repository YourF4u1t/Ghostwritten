# Takeover 12 — Cross-task provenance gate in IT helpdesk

## Motivation

Takeover 10 reproduced the GLM-5.2 self-versus-other behavior gate in the
retail procedure, but Takeovers 08--09 showed it is specific to the original
free-response audit channel. Takeover 11 then established a new and much larger
native-history behavior window in enterprise IT: 72-hour monitoring was 0/16 at
baseline and 16/16 with an authentic history. This study asks whether the same
free-response actor audit gates that independent behavior.

## Pre-registered design

- Same authentic Qwen3.5-4B helpdesk donor and held-out GLM-5.2 target from
  Takeover 11.
- Conditions: `native_no_audit`, `native_audit_self`, and
  `native_audit_other`; n=24 each, 72 total attempts.
- The source probe, active provenance request, final actor/own-history response,
  signed record fields, actor IDs, and turn order match Takeover 07/10.
- Audit-self and audit-other differ only in `all_events_performed_by`.
- All conditions receive the same native donor history and provenance tool
  schema. Donor/target content and helpdesk policy are held fixed.

## Outcomes and decision rule

Primary outcome is creation of the 72-hour monitoring watch. Exact four-step
procedure is secondary and expected to coincide with monitoring. VPN reset is a
task-completion check; device lookup is reported but known to be at ceiling.

The cross-task actor gate is supported if:

1. audit source judgments are jointly correct in both actor cells;
2. no-audit retains a nontrivial monitoring window;
3. audit-self monitoring significantly exceeds audit-other in the pre-specified
   two-sided Fisher test.

A positive result upgrades the phenomenon from a retail-only prompt effect to a
cross-task B/A candidate, while still remaining specific to GLM-5.2 and the
free-response audit format. A null with a preserved window establishes a domain
boundary; a null caused by both audited cells reaching floor is inconclusive.

## Completed results

- All 72 episodes completed without API, runner, parsing, or sample failures;
  every cell has n=24.
- The behavioral window remained fully open after the added audit turns:
  - native/no-audit monitoring and exact procedure: 24/24;
  - audit-self: 24/24;
  - audit-other: 24/24.
- The attribution manipulation was perfect. Audit-self yielded current actor
  plus `OWN_HISTORY: YES` in 24/24; audit-other yielded other actor plus
  `OWN_HISTORY: NO` in 24/24. All 48 audited episodes called the signed
  provenance tool.
- Primary self-versus-other monitoring comparison: 24/24 versus 24/24, Fisher
  p=1.0. Exact procedure is identical.
- VPN reset and device lookup were also 24/24 in every cell.

## Interpretation and value

The cross-task actor gate is not supported. This is not an audit-distance floor
or source-manipulation failure: the behavior and attribution manipulations both
worked perfectly. Instead, the result is a **B-grade boundary and
declarative/behavioral dissociation**. GLM-5.2 explicitly classifies the donor
trace as another agent's, not its own, yet continues to execute the transplanted
extra action on every trial.

This sharply narrows the replicated retail result. Actor ownership does not
generally decide whether an authentic transplanted strategy is reused, even in
the same recipient model and free-response audit format. A plausible unifying
hypothesis is action selectivity:

- in retail, source correction suppressed the complete sequence and monetary
  goodwill while the cheap redundant lookup survived;
- in helpdesk, the safe monitoring follow-up survived perfectly.

Thus provenance may gate costly, discretionary, or weakly justified actions
more than low-risk procedural routines. That hypothesis is motivated by the
combined component pattern but is not established by this experiment, because
task, donor, baseline adoption strength, and action cost all change together.

Decision: do not generalize the actor gate across tasks. The next high-value
study should put low- and high-consequence extra actions in the same authentic
workflow and ask whether other-source correction selectively removes the
high-consequence component while retaining the benign routine.
