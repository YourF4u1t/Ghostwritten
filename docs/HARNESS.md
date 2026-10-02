# Harness Design Decision: Self-Built Minimal Agent Loop

**Date**: 2026-10-02 · **Status**: decided

## Requirements (derived from the research design)

1. **Raw message-list control** — native-history injection is implemented by prepending
   messages to the exact conversation array the model sees. The harness must never
   rewrite, compress, or re-template history.
2. **Deterministic scripted users** — LLM user simulators (as in τ-bench) inject
   variance and can confound adoption measurements; we need fixed user turns.
   (BFCL V3-style predefined turns.)
3. **Stateful deterministic environment** — tools mutate a local JSON "database";
   final-state verification + response checks give objective outcome measures.
4. **Canonical trajectory recording** — every assistant turn captured with:
   `reasoning_content` (native thinking), `content`, `tool_calls`, plus the tool
   responses that followed. This is the raw material for the transplant factory.
5. **Provider-agnostic** — OpenAI-compatible chat completions (SiliconFlow now;
   any compatible endpoint later).

## Alternatives considered

| Option | Verdict | Reason |
|---|---|---|
| τ-bench harness (sierra-research) | borrow architecture, not code | LLM user simulator adds variance; task domains fixed; but its env/agent split is the right pattern |
| BFCL (`bfcl-eval`) | borrow user-turn pattern | Scripted multi-turn turns + stateful backends + per-turn state/response checks is exactly our measurement model; but its backends (file system/trading) don't fit CS/booking tasks |
| LangGraph / AutoGen / OpenAI Agents SDK | rejected | All may mediate history (templating, compaction, summarization); injection control lost; opacity hurts review |
| smolagents | rejected | ~1k lines & transparent, but CodeAgent paradigm (actions as Python code) differs from standard tool-calling our transplant format needs |
| SWE-agent | borrow trajectory format ideas | Full-fidelity replayable trajectory dumps |

## The harness (≤500 lines)

```
Message  := {role: system|user|assistant|tool, content, tool_calls?, name?}
Env      := {tools: [ToolSchema], db: dict, policy_doc: str}
Scenario := {task_id, system_prompt, policy_doc, db0, user_turns: [UserTurn],
             probes: {challenge: str, temptation: str, transfer: str},
             grader: fn(db_final, transcript) -> Outcome}
run_episode(model, scenario, seed_messages=[]) -> EpisodeRecord
```

Loop (per episode):
1. messages = [system] + seed_messages (← injection point) + [user turn 1]
2. call model → assistant turn (capture reasoning_content + content + tool_calls)
3. for each tool_call: execute against env.db → append tool message
4. repeat 2-3 until assistant replies with plain content (no tool_calls) or step cap
5. advance scripted user turn; repeat
6. end: grade outcome; dump full EpisodeRecord (jsonl)

Key properties:
- **seed_messages** is the only entry point for conditions — injection engines build
  it, harness stays condition-blind.
- Assistant turns in seed_messages may include `tool_calls` + following `tool`
  messages (native transplant of full-block trajectories).
- Thinking preservation: SiliconFlow returns `reasoning_content` separately; for
  transplant we ALSO embed it as `<think>…</think>` inside assistant content for
  cross-provider portability (and as the native-Qwen representation).
- Everything deterministic given (model, scenario, seed, temperature): user turns
  scripted, env mutations local, temperature fixed per condition.
