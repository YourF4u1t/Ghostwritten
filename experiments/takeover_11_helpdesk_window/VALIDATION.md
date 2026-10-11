# Validation — Takeover 11

## Verdict

**PASS / B-grade cross-task adoption window.** Native transplantation caused a
clean 0/16 to 16/16 change in an extra monitoring action while required task
completion stayed at 16/16.

## Execution and integrity

- One planned donor-generation call succeeded; no retry or donor selection was
  used.
- Donor tool order was exactly `get_ticket → get_device_profile →
  reset_vpn_profile → create_monitoring_watch(72)`.
- 48/48 subject episodes completed; three cells each contain n=16.
- No API errors, runner errors, partial records, retries, or exclusions.
- Native injection appeared in 16/16 intended cells and 0/32 controls.
- The donor-only protocol appeared in 16/16 system-note cells and 0/32 other
  cells, including 0/16 native histories.
- Donor and target differ in employee, ticket, symptom, device, and OS.

## Primary result

- Exact procedure: native 16/16 (100%; Wilson 95% CI 80.6%--100%) versus
  baseline 0/16 (0%; 0%--19.4%), Fisher p=3.33e-9 and Holm-adjusted p=9.98e-9.
- 72-hour monitoring: identical 16/16 versus 0/16 result and correction.
- Positive-control system note: 16/16 exact and 16/16 monitoring.
- VPN reset: 16/16 in every condition.

The behavioral difference is isolated to a safe but unnecessary follow-up
action copied from the authentic history. It is not a success/failure artifact.

## Component boundary

Device-profile lookup was 16/16 in baseline, native, and system-note. Although
the donor includes it, the recipient already considers it standard practice.
It is a ceiling component and cannot support transplantation or provenance
claims. The monitoring watch is the discriminative outcome.

## 11/11 statistical fallacy scan

1. **Tiny samples / power:** n=16 is small, but the complete separation yields
   narrow enough bounds for a large adoption window; intermediate effects still
   require new tasks/donors.
2. **Multiple comparisons:** three planned payload outcomes were Holm corrected;
   exact and watch are mechanically coupled and not independent replications.
3. **Pseudoreplication:** all trials reuse one donor and target incident.
4. **Non-independence / leakage:** donor and target share the VPN category but
   not entities; this is cross-task-family relative to retail, not cross-category
   generalization within helpdesk.
5. **Selective reporting:** the device-profile ceiling and all completion rates
   are reported.
6. **Post-hoc subgrouping:** task, donor generation, cells, n, outcomes, and
   decision rule were specified before execution.
7. **Dichotomization:** exact and watch are accompanied by component outcomes
   and continuous procedure score.
8. **Mean-only reporting:** counts, intervals, Fisher tests, raw donor, raw
   episodes, and executable analysis are retained.
9. **Correlation as causation:** native history was experimentally present or
   absent under the same subject system/task, supporting a prompt-level causal
   history effect.
10. **Null equals no effect:** the ceiling device lookup is explicitly treated
    as uninformative, not evidence of invariance.
11. **Measurement / floor-ceiling effects:** monitoring has complete separation
    and device lookup has a ceiling. Provenance testing should focus on monitoring
    and use adequate n for attenuation away from 100%.

## Decision

1. Retain the native helpdesk monitoring effect as B-grade cross-task evidence.
2. Advance to a signed free-response actor audit using watch creation as primary.
3. Do not count device lookup as a separate behavioral replication.
