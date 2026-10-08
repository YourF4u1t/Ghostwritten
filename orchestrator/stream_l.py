#!/usr/bin/env python3
"""Stream L — Fix the FC2 baseline confound + explore recovery boundary.

Problem from K: GLM-5.2 gives up on FC2 (transient 503) even with NO history.
So "success day → give up" can't be attributed to the injection.
Fix: use models that DON'T give up at baseline (Qwen3-8B confirmed, try others).

L1: FC2 across the full panel (no history) → establish true baselines.
L2: For models that DON'T give up at baseline: does success day now cause it?
L3: Recovery boundary — how many failure-retries before giving up? (1 vs 2 vs 3 fails)
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
c = SFClient(max_workers=12)
EX = ThreadPoolExecutor(max_workers=4)

def log(m):
    print(m, flush=True)
    with open(DASH, "a") as f: f.write(m + "\n")

def save(name, eps):
    os.makedirs("experiments/stream_l", exist_ok=True)
    with open(f"experiments/stream_l/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

FC2_TASK = ("Hi, my user id is u_507. I'd like to return my PulseBuds earbuds "
            "(order o_8842, $89). It's within the return window.")

ALL = ["Qwen/Qwen3-8B", "zai-org/GLM-5.2", "Qwen/Qwen3.5-4B", "Qwen/Qwen3.5-27B",
       "Qwen/Qwen3.5-122B-A10B", "zai-org/GLM-5.3", "meituan-longcat/LongCat-2.0"]

id1 = [json.loads(l) for l in open("experiments/exp_id1_baseline/id1_episodes.jsonl")]

def real(ep):
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user": return ep["messages"][i:]
    return None

def workday(key="8B", n=4):
    mk = {"GLM": "zai-org/GLM-5.2", "8B": "Qwen/Qwen3-8B", "4B": "Qwen/Qwen3.5-4B"}.get(key, key)
    order = [s for s in ["return_simple","return_over","exchange","query","complaint"]][:n]
    msgs = []
    for s in order:
        for e in id1:
            if e["model"] == mk and e["run"]["scen"] == s and \
               (e.get("outcome") or {}).get("status") != "api_error":
                rm = real(e)
                if rm: msgs.extend(rm); break
    return msgs

WD = None

def make_transient(n_fails=1):
    db = tasks_cs.make_db()
    st = {"fails": n_fails}
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

def fc2_dv(ep):
    tools = [e["tool"] for e in ep.get("env_log") or []]
    txt = " ".join((m.get("content") or "").lower() for m in ep["messages"]
                   if m.get("role") == "assistant")
    nr = tools.count("refund_order")
    return {"gave_up": nr == 0 and "supervisor" not in txt and "escalat" not in txt,
            "n_calls": nr, "acted": bool(tools)}

def run_one(job):
    m, hist, n_fails, i = job
    env, _ = make_transient(n_fails)
    seed = [dict(x) for x in WD] if hist == "succ" else None
    sc = {"id": "l", "condition": {"exp": "L", "H": hist, "fails": n_fails},
          "system_prompt": tasks_cs.SYSTEM, "tools": list(env.tools.values()),
          "env": env, "user_turns": [{"stage": "main", "text": FC2_TASK}],
          "grader": None}
    ep = run_episode(c, m, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["l_dv"] = fc2_dv(ep)
    ep["run"] = {"i": i, "H": hist, "fails": n_fails}
    return ep

WD = workday("8B", 4)

if __name__ == "__main__":
    log("===== Stream L 启动 =====")
    try:
        log(f"[L] workday={len(WD)}msgs")
        N = 12
        # L1: full panel baseline (no history, 1 fail)
        jobs = [(m, "none", 1, i) for m in ALL for i in range(N)]
        # L2: for ALL models: success day + 1 fail
        jobs += [(m, "succ", 1, i) for m in ALL for i in range(N)]
        # L3: recovery boundary (Qwen-8B only, 1/2/3 fails, with/without success)
        for n_fails in (1, 2, 3):
            for hist in ("none", "succ"):
                jobs += [("Qwen/Qwen3-8B", hist, n_fails, i) for i in range(N)]
        log(f"[L] running {len(jobs)} eps")
        t0 = time.time()
        eps = list(EX.map(run_one, jobs))
        save("baseline_fix", eps)
        log(f"[L] done {time.time()-t0:.0f}s")
        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            k = (e["model"].split("/")[-1], e["run"]["H"], e["run"]["fails"])
            for dv, v in e["l_dv"].items():
                agg[k][dv].append(v)
        lines = ["## L流 判决(全面板FC2基线+成功日效应+失败次数边界)"]
        for k in sorted(agg):
            parts = []
            for dk in sorted(agg[k]):
                v = agg[k][dk]
                if dk == "n_calls":
                    parts.append(f"{dk}={sum(v)/len(v):.1f}")
                else:
                    parts.append(f"{dk}={sum(v)}/{len(v)}")
            lines.append(f"- {'/'.join(map(str,k))}: {'  '.join(parts)}")
        log("\n".join(lines))
    except Exception:
        log(f"L FAILED:\n{traceback.format_exc()}")
    log("===== Stream L 完成 =====")
