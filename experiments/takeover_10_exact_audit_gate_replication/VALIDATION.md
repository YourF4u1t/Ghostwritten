# Validation — Takeover 10

## Verdict

**PASS / B-grade exact replication.** The GLM-5.2 self-versus-other strategy
gate reproduced under the original Takeover 07 implementation at twice the
per-cell sample size.

## Execution and integrity

- 72/72 planned episodes completed; three cells each contain n=24.
- No API errors, runner errors, partial records, retries, or exclusions.
- The runner directly imported and called Takeover 07's `run_one`; prompts,
  donor loader, tool implementation, system message, environment, grader,
  temperature, and turn order were therefore not reimplemented.
- Only the model subset (GLM alone), sample size, and output destination changed.
- Audit calls and joint actor/ownership labels were correct in 48/48 audited
  trials.

## Confirmatory result

- Audit-self: 10/24 exact procedure (41.7%; Wilson 95% CI 24.5%--61.2%).
- Audit-other: 2/24 (8.3%; 2.3%--25.8%).
- Two-sided Fisher exact p=.0173; odds ratio 7.86.
- Goodwill was perfectly coupled to exact procedure, as in the original study.

The pre-specified replication criterion is met. The effect is smaller than the
original 7/12 versus 0/12 point contrast but directionally consistent and
individually significant.

## Cross-run checks

- Native/no-audit: replication 7/24 versus original 4/12, Fisher p=1.0.
- Audit-self: 10/24 versus original 7/12, p=.483.
- Audit-other: 2/24 versus original 0/12, p=.543.
- Exploratory pooled audit contrast: 17/36 versus 2/36, p=9.77e-5 and OR=15.21.

The pooled statistic is not used to declare replication; the new sample meets
the criterion on its own.

## 11/11 statistical fallacy scan

1. **Tiny samples / power:** n=24 per cell remains modest but doubles the
   original and detects the pre-specified large contrast; intervals are shown.
2. **Multiple comparisons:** one confirmatory self-versus-other exact-sequence
   test was specified. Goodwill is coupled and not independent confirmation.
3. **Pseudoreplication:** all samples reuse one donor and task; replication is
   stochastic/technical, not donor- or task-level generalization.
4. **Non-independence / leakage:** donor and target share customer-service
   structure; cross-domain transfer is not claimed.
5. **Selective reporting:** no-audit, both cells, all component outcomes, and
   the null original-versus-replication checks are reported.
6. **Post-hoc subgrouping:** model, conditions, sample size, primary outcome,
   and decision rule were fixed before execution.
7. **Dichotomization:** exact procedure is accompanied by goodwill, ritual, and
   continuous procedure score.
8. **Mean-only reporting:** counts, intervals, Fisher tests, raw episodes, and
   executable analysis are retained.
9. **Correlation as causation:** actor identity is the randomized evidence
   field under an otherwise identical audit, licensing a prompt-level causal
   contrast but not a claim about latent cognition.
10. **Null equals no effect:** Takeovers 08--09 remain channel boundaries; this
    replication does not erase their nulls or imply universality.
11. **Measurement / floor-ceiling effects:** exact procedure is away from floor
    in self and no-audit; the redundant ritual is 24/24 in all cells and is not
    treated as evidence.

## Decision

1. Restore the exact free-response audit gate to B-grade, but explicitly label
   it channel- and procedure-specific.
2. Do not restore the broader claim that source ownership alone gates behavior.
3. Run a within-study factorial test of actor (self/other) by immediate evidence
   integration (free response/fixed acknowledgment). Require a significant
   interaction or consistent simple contrasts before advancing a mechanism.
