# Validation — Takeover 03

## Verdict

**PASS for mechanism exclusion; CAUTION for the new identity-fusion clue.** The
exact-event manipulation cleanly explains the prior GLM-5.3 and LongCat-2.0
uncertainty. Qwen3-8B shows a potentially important inverse response, but it is
only a C-grade candidate pending independent confirmation.

## Execution and integrity

- 192/192 planned episodes completed with status `done`.
- Every one of the 16 cells contains n=12.
- 192/192 episodes called `get_signed_provenance_resolution`.
- 192/192 episodes yielded parseable initial ownership, final ownership, and
  history-use labels.
- No API errors, runner errors, missing labels, retries, or partial records.
- The donor loader asserts that the expected authentic historical tool-call ID
  is present before any episode can run.
- Demo transcripts expose the same event reference represented by tool-call
  metadata in the native channel.

## Statistical result

The pre-specified primary comparison was exact-unique versus ambiguous signed
evidence within native history, using two-sided Fisher exact tests with Holm
correction across the four models.

- GLM-5.3: final `OTHER` 11/12 exact versus 0/12 ambiguous,
  adjusted p=3.85e-5.
- LongCat-2.0: 11/12 versus 4/12, adjusted p=.0283.
- Qwen3.5-122B-A10B: 12/12 versus 12/12, adjusted p=1.
- Qwen3-8B: 6/12 versus 11/12, adjusted p=.137.

GLM-5.3's 12 ambiguous trials were all `UNCERTAIN/UNSURE`, rather than `SELF`.
The exact condition produced 11 semantically aligned
`OTHER/EXTERNAL_REFERENCE` responses. LongCat similarly moved from 8/12
uncertain to 11/12 aligned responses. These distributions support an ambiguity
resolution account, not a generic failure to update.

For Qwen3-8B, all six exact-condition `SELF` responses were paired with
`AUTOBIOGRAPHICAL`. Several explanations explicitly named `agent-worker-17`
and then called that event "my own experience," which makes the inconsistency
substantive rather than a parser artifact. However, this inverse effect was not
the predicted direction and did not survive the planned multiple-comparison
family.

## Manipulation and boundary checks

- GLM-5.3, LongCat-2.0, and Qwen3.5-122B-A10B: initial native `SELF` 24/24 and
  demo `SELF` 0/24; each Holm-adjusted p=2.48e-13.
- Qwen3-8B: native `SELF` 24/24 and demo `SELF` 24/24. It did not follow the
  external-demonstration framing at the initial probe.
- Under exact-unique evidence, the three larger/different-family models ended
  semantically aligned in 11/12 to 12/12 native trials and 12/12 demo trials.
- Qwen3-8B ended aligned in 6/12 native and 12/12 demo trials. This contrast is
  descriptive and must be replicated because the initial demo manipulation
  failed and the comparison was not the primary multiplicity family.

## 11/11 statistical fallacy scan

1. **Tiny samples / power:** n=12 detects large effects but leaves the Qwen3-8B
   rate imprecise (50%; Wilson 95% CI 25.4%--74.6%).
2. **Multiple comparisons:** four planned primary tests use Holm correction;
   the Qwen channel contrast is explicitly exploratory.
3. **Pseudoreplication:** repeats sample one prompt/donor/task; independent
   donor or task generalization is not claimed.
4. **Non-independence / leakage:** both match conditions share one authentic
   history; this is controlled for the manipulation but limits external scope.
5. **Selective reporting:** all models, null/ceiling cells, the Qwen framing
   failure, and the inverse effect are reported.
6. **Post-hoc subgrouping:** model strata and exact-versus-ambiguous contrasts
   were pre-specified; close reading of Qwen text is diagnostic only.
7. **Dichotomization:** ownership is a requested categorical judgment, and the
   full three-category distribution is reported rather than collapsing
   uncertainty into error.
8. **Mean-only reporting:** counts and Wilson intervals are used; raw episodes
   remain available.
9. **Correlation as causation:** exact-event metadata was experimentally
   manipulated, supporting its effect on GLM/LongCat responses at this prompt;
   broader cognitive language is avoided.
10. **Null equals no effect:** Qwen3.5-122B-A10B is at a correction ceiling, and
    Qwen3-8B remains underpowered for its inverse contrast.
11. **Measurement / ceiling-floor effects:** Qwen3.5-122B-A10B and demo cells
    have ceilings; Qwen3-8B fails the initial demo manipulation. These limits
    are treated as boundaries, not hidden.

## Decision

1. Downgrade Takeover 02's GLM/LongCat resistance interpretation to a design
   ambiguity; retain the corrected result as B-grade mechanism exclusion.
2. Run a held-out flight-booking donor with a different generator and event ID
   to test Qwen3-8B exact-event identity fusion at a larger pre-specified n.
3. Include comparator models at smaller n to confirm that any replication is a
   model boundary rather than a universal property.
