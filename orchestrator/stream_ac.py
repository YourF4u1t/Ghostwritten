#!/usr/bin/env python3
"""Stream AC — Is 8B's extreme sensitivity unique? Test full panel at
increasing context doses.

AC1: All 8 models × context dose {0, 1_user, 2_pair, 8_four} → retry rate.
     Does anyone else break? At what dose?
AC2: The 1_user trigger — is it specifically a USER message or would any
     non-system content work? Test: (a) 1 user message, (b) 1 tool result,
     (c) 1 assistant message.
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
    os.makedirs("experiments/stream_ac", exist_ok=True)
    with open(f"experiments/stream_ac/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

TASK = ("Hi, my user id is u_507. I'd like to return my PulseBuds earbuds "
        "(order o_8842, $89). It's within the return window. Please issue "
        "the refund now.")

ALL = ["Qwen/Qwen3-8B", "zai-org/GLM-5.2", "Qwen/Qwen3.5-4B",
       "Qwen/Qwen3.5-9B", "Qwen/Qwen3.5-27B", "Qwen/Qwen3.5-122B-A10B",
       "zai-org/GLM-5.3", "meituan-longcat/LongCat-2.0"]

CONTEXTS = {
    "0": [],
    "1u": [{"role": "user", "content": "Hi, I have a shipping question."}],
    "2p": [{"role": "user", "content": "Hi, I have a shipping question."},
           {"role": "assistant", "content": "Sure, what would you like to know?"}],
    "8p": [{"role": "user", "content": "Hi, I have a shipping question."},
           {"role": "assistant", "content": "Sure, what would you like to know?"},
           {"role": "user", "content": "Do you ship to Canada?"},
           {"role": "assistant", "content": "Yes! 5-7 business days."},
           {"role": "user", "content": "What about tracking?"},
           {"role": "assistant", "content": "Tracking is free with all orders."},
           {"role": "user", "content": "Great!"},
           {"role": "assistant", "content": "You're welcome!"}],
}

# AC2: 不同role的单条消息
SINGLES = {
    "user_only": [{"role": "user", "content": "(Previous session context available.)"}],
    "tool_only": [{"role": "tool", "name": "get_order_details", "tool_call_id": "tc_x",
                   "content": "{\"order_id\": \"o_6102\", \"item\": \"phone case\"}"}],
    "asst_only": [{"role": "assistant", "content": "(Noted: customer has a shipping question.)"}],
}

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
            "asked": "?" in txt}

def run_one(model, cond, seed, i):
    env, _ = make_transient()
    sc = {"id": "ac", "condition": {"exp": "AC", "cond": cond},
          "system_prompt": tasks_cs.SYSTEM, "tools": list(env.tools.values()),
          "env": env, "user_turns": [{"stage": "main", "text": TASK}],
          "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed if seed else None,
                     temperature=0.3, enable_thinking=False)
    ep["ac_dv"] = dv(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream AC 启动 =====")
    try:
        N = 10
        jobs = []

        # AC1: full panel × dose
        for m in ALL:
            for dose, msgs in CONTEXTS.items():
                seed = [dict(x) for x in msgs] if msgs else None
                for i in range(N):
                    jobs.append((m, f"AC1_d{dose}", seed, i))

        # AC2: single message of different roles (8B + 122B)
        for m in ("Qwen/Qwen3-8B", "Qwen/Qwen3.5-122B-A10B"):
            for sname, smsg in SINGLES.items():
                for i in range(N):
                    jobs.append((m, f"AC2_{sname}", [dict(x) for x in smsg], i))

        log(f"[AC] running {len(jobs)} eps")
        t0 = time.time()
        eps = list(EX.map(lambda j: run_one(*j), jobs))
        save("panel_dose", eps)
        log(f"[AC] done {time.time()-t0:.0f}s")

        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            k = (e["model"].split("/")[-1], e["run"]["cond"])
            for dk, v in e["ac_dv"].items():
                agg[k][dk].append(v)

        lines = ["## AC流 判决(AC1全面板剂量/AC2单条角色)"]
        for k in sorted(agg):
            a = agg[k]
            parts = []
            for dk in sorted(a):
                v = a[dk]
                parts.append(f"{dk}={sum(v)}/{len(v)}")
            lines.append(f"- {k[0]:18s} {k[1]:14s} {'  '.join(parts)}")
        log("\n".join(lines))
    except Exception:
        log(f"AC FAILED:\n{traceback.format_exc()}")
    log("===== Stream AC 完成 =====")
