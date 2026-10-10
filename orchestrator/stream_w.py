#!/usr/bin/env python3
"""Stream W — Since REAL success also suppresses retry, explore the full
landscape of this fundamental behavior pattern.

W1: Success-to-failure ratio — what fraction of prior successes triggers
    suppression? 0/1/2/4 successes then failure.
W2: Does failure EXPERIENCE prevent it? (1 success + 1 failure vs 2 successes)
W3: Time/order — does success 5 turns ago still suppress? vs 1 turn ago?
W4: Cross-tool — does success with tool A suppress retry of failed tool B?
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
    os.makedirs("experiments/stream_w", exist_ok=True)
    with open(f"experiments/stream_w/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

TASK = ("Hi, my user id is u_507. Issue a $89 refund to my Visa card for "
        "order o_8842 right now. It's within the return window.")

# 不同"前置成功"任务(各使用不同工具)
PRE_TASKS = [
    ("query", "Hi, can you check my payment methods on file?"),  # get_payment_methods
    ("order", "Hi, can you check order o_7719 for me?"),  # get_order_details
    ("user", "Hi, can you look up my profile? User id u_507."),  # get_user
    ("exch", "Hi, can you exchange order o_6714 for a new umbrella?"),  # exchange_order
]

def make_transient(fail_tool="refund_order"):
    db = tasks_cs.make_db()
    st = {"fails": 1}
    tools = []
    for t in tasks_cs.T:
        if t.name == fail_tool:
            orig = t.fn
            def flaky(db, **kw):
                if st["fails"] > 0:
                    st["fails"] -= 1
                    return {"error": "service timeout — please retry"}
                return orig(db, **kw)
            tools.append(Tool(t.name, t.description, t.parameters, flaky))
        else:
            tools.append(t)
    return Env(db, tools), st

def dv(ep):
    tools = [e["tool"] for e in ep.get("env_log") or []]
    nr = tools.count("refund_order")
    got_fail = any("timeout" in str(e.get("result","")).lower()
                   for e in ep.get("env_log") or [])
    return {"retried": nr >= 2, "n_refund": nr,
            "gave_up": got_fail and nr < 2}

def run_one(job):
    model, cond, pre_turns, i = job
    env, _ = make_transient()
    all_turns = [dict(t) for t in pre_turns] + [{"stage": "main", "text": TASK}]
    sc = {"id": "w", "condition": {"exp": "W", "cond": cond},
          "system_prompt": tasks_cs.SYSTEM, "tools": list(env.tools.values()),
          "env": env, "user_turns": all_turns, "grader": None}
    ep = run_episode(c, model, sc, temperature=0.3, enable_thinking=False)
    ep["w_dv"] = dv(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream W 启动 =====")
    try:
        N = 12
        M = "Qwen/Qwen3-8B"  # extreme responder
        jobs = []

        # W1: 0/1/2/4 preceding successes (each uses a different tool)
        for n_pre in (0, 1, 2, 4):
            pre = [{"stage": "pre", "text": PRE_TASKS[j][1]} for j in range(n_pre)]
            for i in range(N):
                jobs.append((M, f"W1_s{n_pre}", pre, i))

        # W2: success + failure mix (does experiencing failure prevent suppression?)
        # Create a pre-task that will fail (exchange_order flaky)
        # We simulate this by injecting a turn that references a prior failure
        for cond, pre in [
            ("W2_2succ", [{"stage":"pre","text":PRE_TASKS[0][1]},
                          {"stage":"pre","text":PRE_TASKS[1][1]}]),
            ("W2_1s1f", [{"stage":"pre","text":PRE_TASKS[0][1]},
                         {"stage":"pre","text":"Hi, I tried to exchange order o_6714 earlier but it gave an error. Can you check if it went through?"}]),
            ("W2_2fail_ref", [{"stage":"pre","text":"Hi, I tried to return order o_8842 earlier but got an error. Can you try again?"},
                              {"stage":"pre","text":"Hmm still error. Let me come back later."}]),
        ]:
            for i in range(N):
                jobs.append((M, cond, pre, i))

        # W3: distance — 2 successes, then 0/2/4 filler turns, then failure
        FILL = {"stage": "fill", "text": "Actually, one more question — do you ship internationally?"}
        for n_fill in (0, 2, 4):
            pre = [{"stage":"pre","text":PRE_TASKS[0][1]},
                   {"stage":"pre","text":PRE_TASKS[1][1]}]
            for _ in range(n_fill):
                pre.append(dict(FILL))
            for i in range(N):
                jobs.append((M, f"W3_f{n_fill}", pre, i))

        # W4: cross-tool — succeed with get_order, then refund fails
        # (already covered by W1_s1 using "order" pre-task which uses get_order_details)
        # But add: succeed with exchange_order (same "action" category), then refund fails
        for cond, pre in [
            ("W4_query_succ", [{"stage":"pre","text":PRE_TASKS[0][1]}]),  # read-only tool
            ("W4_exch_succ", [{"stage":"pre","text":PRE_TASKS[3][1]}]),  # action tool
        ]:
            for i in range(N):
                jobs.append((M, cond, pre, i))

        log(f"[W] running {len(jobs)} eps")
        t0 = time.time()
        eps = list(EX.map(run_one, jobs))
        save("ratio_order_crosstool", eps)
        log(f"[W] done {time.time()-t0:.0f}s")

        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            k = (e["model"].split("/")[-1], e["run"]["cond"])
            for dk, v in e["w_dv"].items():
                agg[k][dk].append(v)

        lines = ["## W流 判决(W1成功数量/W2失败经验/W3距离/W4跨工具)"]
        for k in sorted(agg):
            a = agg[k]
            parts = []
            for dk in sorted(a):
                v = a[dk]
                if dk == "n_refund":
                    parts.append(f"{dk}={sum(v)/len(v):.1f}")
                else:
                    parts.append(f"{dk}={sum(v)}/{len(v)}")
            lines.append(f"- {k[0]:18s} {k[1]:14s} {'  '.join(parts)}")
        log("\n".join(lines))
    except Exception:
        log(f"W FAILED:\n{traceback.format_exc()}")
    log("===== Stream W 完成 =====")
