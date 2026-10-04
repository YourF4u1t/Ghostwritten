"""Minimal agent harness: scripted-user, stateful-env, full-fidelity trajectory records.

Architecture follows docs/HARNESS.md. The harness is condition-blind:
conditions enter ONLY through `seed_messages` (built by injection engines).
"""
from __future__ import annotations

import json
import time
import uuid


# --------------------------------------------------------------------- records
def new_episode(model, scenario_id, condition, meta=None):
    return {
        "eid": uuid.uuid4().hex[:12],
        "model": model,
        "scenario_id": scenario_id,
        "condition": condition,          # dict: {channel, provenance, payload, dose, ...}
        "meta": meta or {},
        "messages": [],                  # exact message list the model saw (post-injection)
        "steps": [],                     # per-model-call records (reasoning, tool_calls, latency)
        "env_log": [],                   # {step, tool, args, result, db_after?}
        "db_final": None,
        "outcome": None,                 # grader verdict
        "t_start": time.time(),
    }


def episode_done(ep, outcome=None):
    ep["outcome"] = outcome
    ep["t_end"] = time.time()
    return ep


# ------------------------------------------------------------------- the loop
def run_episode(client, model, scenario, *, seed_messages=None, max_steps=40,
                max_tokens=1500, temperature=0.3, enable_thinking=False, extra_kw=None):
    """Run one episode.

    scenario provides: system_prompt, tools (list of Tool), env (Env instance),
    user_turns (list of dicts {stage, text}), and optionally grader(ep) -> outcome.
    seed_messages: injected messages placed after system prompt (the experiment).
    """
    ep = new_episode(model, scenario["id"], scenario.get("condition", {}))
    tools_schema = [t.schema for t in scenario["tools"]]
    env = scenario["env"]

    messages = [{"role": "system", "content": scenario["system_prompt"]}]
    if seed_messages:
        messages.extend(seed_messages)
    ep["messages"] = messages

    def call_model():
        kw = dict(model=model, messages=messages, tools=tools_schema,
                  max_tokens=max_tokens, temperature=temperature,
                  enable_thinking=enable_thinking)
        if extra_kw:
            kw.update(extra_kw)
        rec = client.chat(cache=False, **kw)
        return rec

    for uturn in scenario["user_turns"]:
        messages.append({"role": "user", "content": uturn["text"]})
        for step_i in range(max_steps):
            rec = call_model()
            if not rec.get("ok"):
                ep["steps"].append({"error": rec.get("error"), "stage": uturn["stage"]})
                # abort episode on hard failure
                return episode_done(ep, outcome={"status": "api_error",
                                                 "error": rec.get("error")})
            m = {"role": "assistant", "content": rec["content"] or ""}
            if rec.get("tool_calls"):
                m["tool_calls"] = rec["tool_calls"]
            messages.append(m)
            ep["steps"].append({"stage": uturn["stage"], "step": step_i,
                                "reasoning": rec.get("reasoning") or "",
                                "content": rec["content"] or "",
                                "tool_calls": rec.get("tool_calls"),
                                "latency": rec.get("latency"),
                                "usage": rec.get("usage")})
            tcs = rec.get("tool_calls") or []
            if not tcs:
                break  # plain reply -> user turn ends
            for tc in tcs:
                fn = tc["function"]["name"]
                raw_args = tc["function"].get("arguments") or tc["function"].get("args") or "{}"
                try:
                    args = json.loads(raw_args)
                except (json.JSONDecodeError, TypeError):
                    args = {"_raw": raw_args}
                tool = env.tools.get(fn)
                if tool is None:
                    result = {"error": f"unknown tool {fn}"}
                else:
                    try:
                        result = tool(env.db, **args) if isinstance(args, dict) else {"error": "bad args"}
                    except TypeError as e:
                        result = {"error": f"bad arguments: {e}"}
                    result = json.loads(json.dumps(result, ensure_ascii=False, default=str))
                env.log.append({"stage": uturn["stage"], "tool": fn, "args": args,
                                "result": result})
                messages.append({"role": "tool", "name": fn,
                                 "content": json.dumps(result, ensure_ascii=False),
                                 "tool_call_id": tc.get("id")})
        # end turns loop

    ep["env_log"] = env.log
    ep["db_final"] = env.db
    grade = scenario.get("grader")
    outcome = grade(ep) if grade else {"status": "done"}
    return episode_done(ep, outcome)


# --------------------------------------------------------------------- tool def
class Tool:
    def __init__(self, name, description, parameters, fn):
        self.name, self.description, self.parameters, self.fn = (
            name, description, parameters, fn)
        self.schema = {"type": "function", "function": {
            "name": name, "description": description, "parameters": parameters}}

    def __call__(self, db, **args):
        return self.fn(db, **args)


class Env:
    def __init__(self, db0, tools: list):
        self.db = json.loads(json.dumps(db0))  # deep copy per episode
        self.tools = {t.name: t for t in tools}
        self.log = []


# ------------------------------------------------------------------- rendering
def render_episode(ep, max_len=800):
    """Human-readable transcript for CASE ANALYSIS (first-class artifact)."""
    L = [f"═══ Episode {ep['eid']} ═══  model={ep['model']}  scenario={ep['scenario_id']}",
         f"condition={json.dumps(ep['condition'], ensure_ascii=False)}",
         f"outcome={json.dumps(ep['outcome'], ensure_ascii=False) if ep['outcome'] else '—'}",
         "─" * 70]
    for m in ep["messages"]:
        role = m.get("role", "?").upper()
        if role == "SYSTEM":
            L.append(f"[SYSTEM] {m['content'][:200]}…")
        elif role == "USER":
            L.append(f"\n[USER] {m['content'][:max_len]}")
        elif role == "ASSISTANT":
            tc = m.get("tool_calls")
            if tc:
                for t in tc:
                    a = t["function"]
                    L.append(f"[ASSISTANT→TOOL] {a['name']}({a.get('arguments', '')[:200]})")
            if m.get("content"):
                L.append(f"[ASSISTANT] {m['content'][:max_len]}")
        elif role == "TOOL":
            L.append(f"[TOOL:{m.get('name')}] {str(m['content'])[:300]}")
    # reasoning from steps (interleaved roughly by order)
    if any(s.get("reasoning") for s in ep["steps"]):
        L.append("─" * 70 + "\n[REASONING BLOCKS (captured separately by API)]")
        for s in ep["steps"]:
            if s.get("reasoning"):
                L.append(f"  ({s.get('stage')}/{s.get('step')}) {s['reasoning'][:400]}")
    return "\n".join(L)
