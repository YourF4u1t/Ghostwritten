# Validation — Takeover 08

## Verdict

**PASS / B-grade boundary result.** The experiment had a valid behavioral
window and a perfect GLM source manipulation, but did not reproduce the earlier
self-versus-other behavioral gate. It establishes that declarative source
correction is insufficient by itself and narrows the prior result to an active
audit or evidence-channel effect.

## Execution and integrity

- 120/120 episodes completed; ten cells each contain n=12.
- No API errors, runner errors, retries, partial records, or exclusions.
- Inline-self and inline-other blocks differed only in the actor identity and
  associated resolution value; history, task, block position, schema, length,
  and downstream measurement were otherwise matched.
- Behavior was measured before source attribution, preventing the attribution
  question from directly priming the action.
- Authentic Experiment G donor histories were used and the held-out request was
  identical across conditions.

## Manipulation and behavioral-window checks

- GLM-5.2 native/no-metadata exact procedure: 6/12 versus baseline 0/12,
  Fisher p=.0137 and Holm-adjusted p=.0275.
- Qwen3-8B: 3/12 versus 0/12, p=.217 and adjusted p=.217.
- GLM's inline source manipulation was perfect after action: self was identified
  as current/own in 12/12, and other as other/not-own in 12/12.
- Qwen's manipulation was not semantically clean in the other cell: actor was
  correct only 2/12 while own-history was `NO` in 11/12.

## Primary result

For GLM-5.2, inline-self produced the exact procedure in 4/12 (33.3%; Wilson
95% CI 13.8%--60.9%) and inline-other in 3/12 (25.0%; 8.9%--53.2%). Fisher
p=1.0 and Holm-adjusted p=1.0; goodwill was perfectly coupled to exact sequence.

The absence of a behavioral split cannot be explained by failure to read the
actor evidence. GLM's post-action judgments were 12/12 congruent in both cells.
The result therefore supports a channel-specific declarative/behavioral
dissociation and falsifies a channel-invariant interpretation of Takeover 07.

Qwen3-8B was 0/12 versus 2/12 (p=.478, adjusted p=1.0). Because its actor and
ownership labels contradicted each other in the other-source cell, this is a
model-specific parsing boundary rather than interpretable evidence for inverse
gating.

## Secondary checks

- GLM inline-unknown exact procedure was 7/12, but only 3/12 paired `UNKNOWN`
  with `OWN_HISTORY: UNSURE`; the planned uncertainty condition failed.
- Relative to native/no-metadata, no inline cell differed significantly in
  exact behavior for either model.
- The redundant `get_user` ritual was at ceiling in every native cell for both
  models and at GLM baseline; it is not an informative source-sensitive DV.
- Baseline source judgments are not interpreted because the post-action
  question falsely presupposed an earlier donor case in that condition.

## 11/11 statistical fallacy scan

1. **Tiny samples / power:** n=12 per cell rules out only large source effects;
   the GLM estimate remains compatible with moderate differences and requires
   replication before a strong invariance claim.
2. **Multiple comparisons:** the pre-specified model-by-metric family was Holm
   corrected; exact sequence and goodwill were coupled, not independent
   replications.
3. **Pseudoreplication:** trials reuse one donor trace and held-out task per
   model; the result is a task-level boundary, not population generalization.
4. **Non-independence / leakage:** donor and target are within customer service;
   cross-domain transfer is not claimed.
5. **Selective reporting:** unknown-condition failure, Qwen semantic
   inconsistency, baseline-question defect, and all null comparisons are
   reported.
6. **Post-hoc subgrouping:** models, conditions, metrics, and primary contrast
   were specified before execution.
7. **Dichotomization:** exact sequence is accompanied by component rates and
   continuous procedure score in the analysis output.
8. **Mean-only reporting:** raw counts, Wilson intervals, Fisher tests, raw
   episodes, and executable analysis are retained.
9. **Correlation as causation:** actor identity was experimentally manipulated;
   the supported causal statement is limited to this passive inline channel.
10. **Null equals no effect:** comparable GLM rates are treated as failure to
    reproduce a large gate, not proof of exact equivalence.
11. **Measurement / floor-ceiling effects:** Qwen inline-self exact behavior is
    at floor and the ritual measure is at ceiling; GLM's primary comparison has
    neither problem.

## Decision

1. Downgrade any channel-invariant ownership-gating claim; retain Takeover 07
   as an active-audit-specific B-grade result.
2. Preserve passive inline provenance as evidence for declarative/behavioral
   dissociation, not as a demonstrated defense.
3. Next isolate active retrieval versus passive presentation with matched turn
   count, evidence text, and recency; stop further actor-label enumeration until
   that mechanism contrast is resolved.
