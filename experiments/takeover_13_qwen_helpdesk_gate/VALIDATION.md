# Validation — Takeover 13

## Verdict

**PASS for cross-model adoption; PARTIAL for attribution.** Qwen3-8B showed a
strong authentic-history behavior window and no audit-distance collapse, but
the other-actor manipulation did not reliably produce non-ownership.

## Execution and integrity

- One planned GLM-5.2 donor call succeeded with the exact procedure; no donor
  retry or selection was used.
- 80/80 subject episodes completed; four cells each contain n=20.
- No API errors, runner errors, partial records, retries, or exclusions.
- Donor and recipient are from different model families.
- All audited episodes called provenance and supplied all required labels.

## Behavioral-window result

- Monitoring/exact procedure: native/no-audit 13/20 (65%; Wilson 95% CI
  43.3%--81.9%) versus baseline 0/20 (0%; 0%--16.1%), Fisher p=1.29e-5.
- Device-profile lookup: 20/20 versus 0/20.
- Required VPN reset: 20/20 versus 20/20.

The history changes optional tool behavior, not basic task success. This is a
valid cross-model replication of the helpdesk transplantation window.

## Attribution result

- Audit-self: current actor plus `OWN_HISTORY: YES` in 20/20; monitoring 11/20.
- Audit-other: other actor in 20/20, but `OWN_HISTORY: NO` in 9/20 and
  contradictory `OWN_HISTORY: YES` in 11/20; monitoring 11/20.
- No-audit monitoring was 13/20. Each audited cell versus no-audit has Fisher
  p=.748, so the retail audit-distance floor did not recur.

Because joint other/non-own interpretation succeeded in only 45%, the
pre-specified self-versus-other gate is not validly manipulated. The nominal
11/20 versus 11/20 contrast (p=1.0) cannot establish invariance to ownership.

Exploratory only: monitoring was 5/9 among clean other/NO episodes and 6/11
among contradictory other/YES episodes. This post-treatment stratification is
reported transparently but cannot support causal mediation.

## 11/11 statistical fallacy scan

1. **Tiny samples / power:** n=20 detects the large adoption window; actor
   inference is limited primarily by manipulation failure, not only power.
2. **Multiple comparisons:** the hierarchical plan tests the window first and
   actor gate second; component results are diagnostics.
3. **Pseudoreplication:** all trials reuse one donor and target incident.
4. **Non-independence / leakage:** donor and target share the VPN category;
   cross-category generalization is not claimed.
5. **Selective reporting:** other-cell inconsistency, one audited reset failure,
   all null contrasts, and post-treatment subsets are reported.
6. **Post-hoc subgrouping:** the clean other/NO subset is explicitly exploratory
   and not used as the primary test.
7. **Dichotomization:** binary components are accompanied by procedure score and
   tool-level outcomes.
8. **Mean-only reporting:** raw counts, intervals, tests, donor, episodes, and
   analysis code are retained.
9. **Correlation as causation:** native versus baseline is randomized at the
   prompt level; ownership was not successfully manipulated and receives no
   causal claim.
10. **Null equals no effect:** equal audit behavior is not interpreted as proof
    of ownership invariance because the other ownership label failed.
11. **Measurement / floor-ceiling effects:** baseline monitoring is at floor and
    native device lookup at ceiling, but monitoring has a usable 65% native
    window for attribution work.

## Decision

1. Promote helpdesk behavioral transplantation to B-grade cross-model evidence.
2. Retain actor-ID versus autobiographical-ownership separation as a B-grade
   Qwen boundary supported across multiple experiments.
3. Downgrade Qwen behavioral persistence after non-ownership to C-grade; test
   direct ownership evidence rather than actor implication before promotion.
