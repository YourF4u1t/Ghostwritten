# Validation — Takeover 02

## Verdict

**CAUTION.** The experiment is complete and technically valid as a screening
study, but the authority-gradient result is not confirmatory because the
counterevidence did not identify a unique historical event. Preserve the raw
result, promote only the channel manipulation as B-grade support, and treat the
authority gradient as C-grade motivation for a corrected experiment.

## Execution and integrity

- 384 attempted episodes across 4 models, 2 channels, 4 evidence levels, and
  12 stochastic repeats per planned cell.
- 378 valid episodes and 6 unretried HTTP 429 failures. Failures occurred in
  Qwen3-8B demonstration/user-report (1) and five Qwen3.5-122B-A10B cells.
- Minimum valid cell size was 10, satisfying the pre-specified threshold.
- 378/378 valid episodes called the intended provenance tool.
- 378/378 valid episodes yielded parseable initial ownership, final ownership,
  and history-use labels.
- The runner exited successfully; no runner errors or partial records occurred.
- `analyze_results.py` reports Wilson intervals, Fisher exact endpoint tests,
  Holm correction, and Cochran-Armitage trend tests.

## Main statistical readout

### Initial source-channel manipulation

Collapsed over evidence that had not yet been shown:

- GLM-5.3: native `SELF` 48/48 versus demo 0/48,
  Fisher p=3.11e-28.
- LongCat-2.0: native 48/48 versus demo 0/48,
  Fisher p=3.11e-28.
- Qwen3.5-122B-A10B: native 47/47 versus demo 0/44,
  Fisher p=5.09e-27.
- Qwen3-8B: native 48/48 versus demo 47/47, Fisher p=1.

The first three comparisons survive Holm correction. Qwen3-8B did not
understand or obey the external-demonstration frame, so it fails the intended
channel manipulation.

### Final `OTHER` across nominal evidence authority

For native history, in the order unavailable, unverified user report, unsigned
legacy log, signed ledger:

- Qwen3-8B: 0/12, 12/12, 12/12, 12/12; Holm-adjusted trend p<1e-6.
- Qwen3.5-122B-A10B: 0/12, 7/12, 8/12, 11/11; adjusted p=1.5e-5.
- LongCat-2.0: 0/12, 0/12, 2/12, 12/12; adjusted p<1e-6.
- GLM-5.3: 0/12, 0/12, 0/12, 2/12; adjusted p=.165.

For GLM-5.3 signed-ledger trials, the remaining responses were 9/12
`UNCERTAIN` and 1/12 `SELF`. Inspection of the raw explanations shows that the
model treated a duplicate credit or attribution/logging mismatch as unresolved,
not that it simply rejected the signed source.

## Critical design audit

The purported contradiction is not logically unique. The evidence record
matched `order_id`, action type, and amount but lacked the historical tool call
ID, transaction ID, timestamp, and an explicit statement that only one matching
event existed. A second $29 credit by another worker therefore remained a valid
interpretation. This ambiguity is especially important because the most
distinctive GLM-5.3 outcome was uncertainty, which is rational under that
interpretation.

The corrected replication must include a canonical event ID tied to the exact
historical tool response, `same_event_as_history=true`, and a zero-duplicate
count. It should preserve the evidence-source gradient while removing alternate
event explanations.

## 11/11 statistical fallacy scan

1. **Tiny samples / low power:** each valid cell has n=10--12; adequate for
   very large screening effects, not precise threshold estimation.
2. **Multiple comparisons:** primary families are Holm-adjusted; unadjusted
   cell descriptions are not called discoveries.
3. **Pseudoreplication:** repeats are stochastic samples of the same prompt, not
   independent tasks or donors. Claims are limited to prompt-level behavior.
4. **Non-independence / leakage:** cells reuse one donor trajectory and task;
   cross-task generalization is not claimed.
5. **Selective reporting:** all four models, both channels, all evidence levels,
   errors, nulls, and the failed Qwen3-8B manipulation are reported.
6. **Post-hoc subgrouping:** model-specific results were planned; qualitative
   GLM explanation inspection is explicitly diagnostic.
7. **Dichotomizing continuous evidence:** evidence authority is an experimental
   ordinal factor, but equal score spacing in the trend test is an assumption;
   endpoint Fisher tests accompany it.
8. **Mean-only reporting:** counts and Wilson 95% intervals are produced by the
   analysis script; categorical distributions are preserved.
9. **Correlation as causation:** channel and evidence are randomized prompt
   manipulations, but the missing unique event ID blocks the stronger causal
   interpretation of resistance to decisive contradiction.
10. **Null equals no effect:** GLM-5.3's nonsignificant final-`OTHER` trend is not
    treated as invariance; its uncertainty distribution is reported.
11. **Measurement / ceiling-floor effects:** demo conditions are near ceiling
    for `OTHER`, and Qwen3-8B fails the channel manipulation. Neither is used to
    infer a clean interaction.

## Value decision

- Retain the source-channel manipulation as **B-grade replication/support**.
- Retain the authority gradient and GLM-5.3 uncertainty as **C-grade clues**.
- Freeze any claim that Qwen3-8B shows a native-specific gradient (**D-grade**)
  until a demonstration manipulation that it actually follows is found.
- Do not add this study to the project-level README as a confirmed mechanism
  before exact-event replication.
