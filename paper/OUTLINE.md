# Paper Outline — v0.1 (working draft)

**Title (candidates)**
- Transplanted Trajectories: How Injected Agent Histories Rewrite Memory, Not Behavior
- Whose Experience Is It Anyway? Injection, Replay, and Behavioral Lock-in in LLM Agents
- One Shot Is Enough: History Injection and Self-Sustaining Behavior Change in LLM Agents

## Abstract sketch
We study what happens when a model-generated agent trajectory — produced authentically
by another model — enters an agent's context through different epistemic channels:
as its own session history (native), as an in-context example (demo), or as an
explicit instruction. Across ~3,600 episodes, 8 models, 3 domains (retail CS,
booking, coding), we find a systematic dissociation: **native channel rewrites
autobiographical memory (universal, provenance-blind, dose-robust, correction-
resistant); demo channel drives behavioral imitation (conditional on procedure
structure, policy compatibility, scenario framing); instructions control actions
(including overriding hardened policy) but leave memory intact.** Crucially, one
successful induction plus standard experience replay yields **multi-generational
behavioral lock-in (92–96% at generation 3, no re-injection)**, and instruction-
induced policy violations persist after instruction removal (73%). A single
contradictory self-experience collapses lock-in regardless of order — a cheap
mitigation. Strong/newer models are resistant at the induction gate; weaker/older
models are the vulnerable population.

## 1. Introduction
- Agent memory/experience replay is now standard (compaction, Reflexion/ExpeL-style
  experience, trajectory libraries, agent handoff) → the integrity of "what I did"
  becomes load-bearing.
- Threat/phenomenon: transplanted trajectories (model-generated, authentic-format).
- Contributions:
  C1 Channel×function dissociation (memory vs behavior vs policy).
  C2 Lock-in: one-shot induction → self-sustaining via replay (incl. post-instruction
     persistence); dose-response of counter-examples.
  C3 Mechanism: attribution is label-gated (GLM) vs position-ubiquitous (Qwen3-8B);
     imitation is invitation-gated; correction backfires; scenario framing modulates.
  C4 Boundary + population: verifiable/ceiling tasks immune; induction-gate split
     (strong/newer models resist).

## 2. Related work (from LITERATURE notes)
- Role Confusion / CoT Forgery (ICML'26); Subliminal learning (Nature'26);
  memory poisoning family (MINJA, MPBench, GhostWriter, Sleeper, Memory Laundering);
  many-shot jailbreak; Lost-in-multi-turn; Leveraging ICL for agents; W2S literature
  (fine-tuning only); EvilGenie/reward hacking; provenance/signing defenses.
- Delta: none compares channels×provenance under event-matched content; none shows
  replay-based lock-in/generational persistence; none maps the counter-example cure.

## 3. Setup
- Testbeds (CS/BOOK/coding), trajectory factory (ops-note elicitation, purity checks),
  channels (native/demo/instruction; event-matched vs rule-equivalent), measurement
  stack (rule-based env-log DVs; quote-verified dual judges κ=0.943; keyword-validated
  memory DV 100%), manipulation checks, content-anchored stage extraction.

## 4. Memory channel (F1)
native → universal first-person assimilation (7-8 models, 5-8/8~12/12), provenance-
blind (C), dose-robust (B), cross-domain (D), correction-resistant + backfire (H2),
person-scoped vs blind taxonomy (H1), phantom verbal claims in excluded-label
conditions (H3 7/12), no drift across generations (M3).

## 5. Behavior channel (E/G/K/W2S/M1/M5)
- Adoption requires: procedure structure (12/12 vs 7/12 isolated), policy-compat
  (violations 0/12), invitation framing (neutral≈native low), scenario framing (O),
  model membership (induction gate: strong 0/20 vs weak 10-15/20).
- Coding domain: zero contagion even blind (K) → ceiling/task-affordance boundary.

## 6. Lock-in and persistence (J/J2/J3/L/N)
- Self-replay lock-in (94-98%), generational persistence (92-96% gen3),
  post-instruction violation persistence (73%), counter-example cure (72%→0-11%,
  order-independent; dose curve N), cross-task boundary (M2), scenario-generality
  variation (GLM narrow vs Qwen3-8B broad).

## 7. Policy hierarchy (I)
instruction > hardened policy > precedent (0/12) — and the security reading:
one instruction + replay = persistent violation even after removal.

## 8. Discussion
- Implications for agent memory design (replay curation, counter-example
  interleaving, provenance labels — and their insufficiency), model selection
  (induction gate), auditing (memory ≠ behavior integrity).
- Limitations: single-organization open-model panel; scripted users; N per cell;
  scenario specificity; elicitation notes for payloads.

## Appendix
- Case/vignette library (20+); correction/retraction log; full per-cell tables.
