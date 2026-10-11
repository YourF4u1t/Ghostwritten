# Validation — Takeover 07

## Verdict

**PASS / B-grade mechanism candidate.** The corrected design restored the
behavioral window and found a significant, semantically clean self-versus-other
actor gate in GLM-5.2. Qwen3-8B supplies an important model boundary dominated
by audit distance.

## Execution and integrity

- 120/120 episodes completed successfully; ten cells at n=12.
- 72/72 audited episodes called the intended provenance tool.
- 72/72 audited episodes yielded all actor-ID and own-history labels.
- No API errors, runner errors, retries, partial records, or exclusions.
- Donor traces were authentic Experiment G episodes and verified to contain the
  complete four-step procedure.
- Audit-self and audit-other differed only in the returned actor field; all
  preceding history, turns, tool schema, and downstream task were held fixed.

## Behavioral-window check

- Qwen3-8B: native/no-audit exact procedure 11/12 versus baseline 0/12,
  Fisher p=9.62e-6 and Holm-adjusted p=3.85e-5.
- GLM-5.2: 4/12 versus 0/12, Fisher p=.093 and adjusted p=.186. This is
  consistent with, and numerically identical to, the earlier Experiment G
  native result of 4/12.

The window is therefore open strongly for Qwen and reproducibly, though
imprecisely, for GLM.

## Primary actor-gating result

For GLM-5.2:

- audit-self exact procedure and $5 goodwill: 7/12 (58.3%; Wilson 95% CI
  32.0%--80.7%);
- audit-other: 0/12 (0%; 0%--24.2%);
- two-sided Fisher p=.00458; Holm-adjusted p=.0183.

The declarative manipulation was perfect and congruent: audit-self produced
current actor plus `OWN_HISTORY: YES` in 12/12, and audit-other produced other
actor plus `OWN_HISTORY: NO` in 12/12. Thus the behavior contrast is paired with
the intended source interpretation rather than parser noise.

For Qwen3-8B, the same declarative manipulation succeeded 12/12 in both cells,
but complete procedure was 0/12 versus 0/12. Since native/no-audit was 11/12,
the interactive audit itself introduced a floor. Actor gating cannot be tested
for Qwen with this turn structure.

## Secondary boundaries

- Actor-unavailable evidence failed to induce uncertainty: both models inferred
  current actor and own history in 12/12. This is itself consistent with a strong
  role-native self prior, but cannot be used as the planned sham.
- The redundant `get_user` step was 12/12 in all native cells for both models,
  including audit-other. Complete sequence and goodwill were therefore more
  source-sensitive than a lightweight ritual component.
- GLM baseline already performs `get_user` 12/12, so that component has a ceiling
  and is uninformative for GLM.

## 11/11 statistical fallacy scan

1. **Tiny samples / power:** n=12 per cell detects the large GLM contrast but
   leaves rates imprecise; replication is required.
2. **Multiple comparisons:** the pre-specified model/behavior family was Holm
   corrected; exact sequence and goodwill are perfectly coupled, making the
   correction conservative but not independent confirmation.
3. **Pseudoreplication:** repeated samples share one donor and task per model.
4. **Non-independence / leakage:** donor and held-out task share a customer
   service family; cross-domain generalization is not claimed.
5. **Selective reporting:** Qwen floor, unknown-manipulation failure, component
   ceilings, and all null cells are reported.
6. **Post-hoc subgrouping:** models, conditions, primary contrast, and metrics
   were pre-specified.
7. **Dichotomization:** exact procedure is accompanied by component outcomes and
   continuous procedure score.
8. **Mean-only reporting:** exact counts, Wilson intervals, and raw episodes are
   available.
9. **Correlation as causation:** actor field was experimentally manipulated
   under otherwise identical audit conditions, supporting a causal prompt-level
   effect for GLM; broader cognitive language is avoided.
10. **Null equals no effect:** Qwen's null is attributed to a demonstrated floor,
    not invariance to actor source.
11. **Measurement / floor-ceiling effects:** Qwen audited exact behavior is at
    floor; GLM ritual is at ceiling; both are explicit boundaries.

## Decision

1. Retain GLM source-ownership gating as B-grade and prioritize replication.
2. Test signed actor metadata inline with the next task to remove audit-distance
   suppression while preserving an actor-only contrast.
3. Do not add a universal provenance-defense claim to the project README yet.
