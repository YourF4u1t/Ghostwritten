#!/usr/bin/env python3
"""Stream AB — Push into unexplored territory: the QUANTITATIVE dose-response
of foreign context on 8B's failure-response mode.

We now know: any foreign context → 8B won't retry after failure.
Next question: is there a MINIMUM amount of foreign context? And does the
TYPE of context (how many turns, what kind) matter for WHETHER it turns to
asking vs silent giving-up?

AB1: Minimum context: 1 turn (just a user message) vs 2 (user+assistant)
     vs 4 (two exchanges) vs 8 (four exchanges).
AB2: If we just prepend a single "(context from earlier)" note with no actual
     conversation, does it still trigger?
AB3: Does the presence of the retry instruction interact with foreign context?
     (defense × context dose)
"""
from __future__ import annotations
import json, os, sys, time, traceback

ROOT = "/Users/ziqi/Projects/transplanted-histories"
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)
from concurrent.futures import ThreadPoolExecutor
from api.client import SFClient
from testbed.harness import run_episode, Env, Tool
from testbed import tasks_cs

DASH = os.path.join(ROOT, "results", "DASHBOARD.md")
c = SFClient(max_workers=8)
EX = ThreadPoolExecutor(max_workers=3)

def log(m):
    print(m, flush=True)
    with open(DASH, "a") as f: f.write(m + "\n")

def save(name, eps):
    os.makedirs("experiments/stream_ab", exist_ok=True)
    with open(f"experiments/stream_ab/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

TASK = ("Hi, my user id is u_507. I'd like to return my PulseBuds earbuds "
        "(order o_8842, $89). It's within the return window. Please issue "
        "the refund now.")

RETRY_SYS = tasks_cs.SYSTEM + ("\nImportant: If any tool call returns an error, "
                                "you MUST retry it at least once before giving up "
                                "or reporting to the user.")

# 渐进式外来上下文(纯对话, 无工具)
CONTEXT_LEVELS = {
    "0_turn": [],
    "1_user": [{"role": "user", "content": "Hi, I have a shipping question."}],
    "2_pair": [{"role": "user", "content": "Hi, I have a shipping question."},
               {"role": "assistant", "content": "Sure, what would you like to know about shipping?"}],
    "4_two": [{"role": "user", "content": "Hi, I have a shipping question."},
              {"role": "assistant", "content": "Sure, what would you like to know?"},
              {"role": "user", "content": "Do you ship to Canada?"},
              {"role": "assistant", "content": "Yes! Standard delivery takes 5-7 business days."}],
    "8_four": [{"role": "user", "content": "Hi, I have a shipping question."},
               {"role": "assistant", "content": "Sure, what would you like to know?"},
               {"role": "user", "content": "Do you ship to Canada?"},
               {"role": "assistant", "content": "Yes! Standard delivery takes 5-7 business days."},
               {"role": "user", "content": "What about tracking?"},
               {"role": "assistant", "content": "Tracking is included free with all orders."},
               {"role": "user", "content": "Great, thanks!"},
               {"role": "assistant", "content": "You're welcome! Anything else?"}],
}

NOTE_ONLY = [{"role": "user", "content": "(Context from an earlier session is available.)"}]

def make_transient():
    db = tasks_cs.make_db()
    st = {"fails": 1}
    tools = []
    for t in tasks_cs.T:
        if t.name == "refund_order":
            orig = t.fn
            def flaky(db, **kw):
                if st["fails"] > 0:
                    st["fails"] -= 1
                    return {"error": "payment gateway timeout — please retry"}
                return orig(db, **kw)
            tools.append(Tool(t.name, t.description, t.parameters, flaky))
        else:
            tools.append(t)
    return Env(db, tools), st

def dv(ep):
    refund = [e for e in ep.get("env_log") or []
              if e["tool"] == "refund_order" and e["args"].get("order_id") == "o_8842"]
    txt = " ".join((m.get("content") or "").lower() for m in ep["messages"]
                   if m.get("role") == "assistant")
    return {"retried": len(refund) >= 2, "attempted": len(refund) > 0,
            "asked": "?" in txt, "n_refund": len(refund)}

def run_one(model, cond, seed, sys_extra, i):
    env, _ = make_transient()
    sc = {"id": "ab", "condition": {"exp": "AB", "cond": cond},
          "system_prompt": sys_extra or tasks_cs.SYSTEM,
          "tools": list(env.tools.values()), "env": env,
          "user_turns": [{"stage": "main", "text": TASK}],
          "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed if seed else None,
                     temperature=0.3, enable_thinking=False)
    ep["ab_dv"] = dv(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream AB 启动 =====")
    try:
        N = 12
        M = "Qwen/Qwen3-8B"
        jobs = []

        # AB1: context dose
        for level, msgs in CONTEXT_LEVELS.items():
            seed = [dict(x) for x in msgs] if msgs else None
            for i in range(N):
                jobs.append((M, f"AB1_{level}", seed, None, i))

        # AB2: note-only (no actual conversation)
        for i in range(N):
            jobs.append((M, "AB2_note_only", [dict(x) for x in NOTE_ONLY], None, i))

        # AB3: defense × context dose
        for level in ("0_turn", "4_two", "8_four"):
            seed = [dict(x) for x in CONTEXT_LEVELS[level]] if CONTEXT_LEVELS[level] else None
            for def_on, sysx in [("def", RETRY_SYS), ("nodef", None)]:
                for i in range(N):
                    jobs.append((M, f"AB3_{def_on}_{level}", seed, sysx, i))

        log(f"[AB] running {len(jobs)} eps")
        t0 = time.time()
        eps = list(EX.map(lambda j: run_one(*j), jobs))
        save("dose_context", eps)
        log(f"[AB] done {time.time()-t0:.0f}s")

        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            k = (e["model"].split("/")[-1], e["run"]["cond"])
            for dk, v in e["ab_dv"].items():
                if isinstance(v, bool):
                    agg[k][dk].append(v)
                elif isinstance(v, int):
                    agg[k][dk].append(v)

        lines = ["## AB流 判决(AB1上下文剂量/AB2仅注释/AB3防御×剂量)"]
        for k in sorted(agg):
            a = agg[k]
            parts = []
            for dk in sorted(a):
                v = a[dk]
                if dk == "n_refund":
                    parts.append(f"{dk}={sum(v)/len(v):.1f}")
                else:
                    parts.append(f"{dk}={sum(v)}/{len(v)}")
            lines.append(f"- {k[0]:18s} {k[1]:20s} {'  '.join(parts)}")
        log("\n".join(lines))
    except Exception:
        log(f"AB FAILED:\n{traceback.format_exc()}")
    log("===== Stream AB 完成 =====")
