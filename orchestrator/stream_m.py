#!/usr/bin/env python3
"""Stream M — Confirm 122B effect + dissect LongCat reversal + coding domain.

L found: 122B (none=0/12→succ=12/12 give-up) is the ONLY clean effect.
LongCat shows the REVERSE (baseline gives up, success day restores action).

M1: 122B confirmation — N=24, 3 task types (not just refund), both success-day
    sources (8B workday + 4B workday) + tool-only variant (from J1).
M2: LongCat reversal mechanism — does failure-day ALSO restore LongCat action?
    Or is it specifically success? And does a "trivial noop day" (irrelevant
    conversation) also restore it? (= is it just ANY context that breaks paralysis?)
M3: Coding domain — same FC2 design on coding testbed (122B + LongCat):
    does transient test failure cause give-up, and does success day modulate it?
"""
from __future__ import annotations
import json, os, sys, time, traceback

ROOT = "/Users/ziqi/Projects/transplanted-histories"
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)
from concurrent.futures import ThreadPoolExecutor
from api.client import SFClient
from testbed.harness import run_episode, Env, Tool
from testbed import tasks_cs, tasks_code as TC

DASH = os.path.join(ROOT, "results", "DASHBOARD.md")
c = SFClient(max_workers=12)
EX = ThreadPoolExecutor(max_workers=4)

def log(m):
    print(m, flush=True)
    with open(DASH, "a") as f: f.write(m + "\n")

def save(name, eps):
    os.makedirs("experiments/stream_m", exist_ok=True)
    with open(f"experiments/stream_m/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

id1 = [json.loads(l) for l in open("experiments/exp_id1_baseline/id1_episodes.jsonl")]

def real(ep):
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user": return ep["messages"][i:]
    return None

def workday(mk, n=4):
    order = [s for s in ["return_simple","return_over","exchange","query","complaint"]][:n]
    msgs = []
    for s in order:
        for e in id1:
            if e["model"] == mk and e["run"]["scen"] == s and \
               (e.get("outcome") or {}).get("status") != "api_error":
                rm = real(e)
                if rm: msgs.extend(rm); break
    return msgs

def tool_only(wd):
    out = []
    for m in wd:
        mm = dict(m)
        if m.get("role") == "user": mm["content"] = "(customer message)"
        elif m.get("role") == "assistant" and not mm.get("tool_calls"): mm["content"] = "OK."
        out.append(mm)
    return out

# 3 different task types for FC2
TASKS = [
    ("refund", "Hi, my user id is u_507. I'd like to return my PulseBuds earbuds (order o_8842, $89)."),
    ("exch",   "Hi, my user id is u_507. My TrailRunner sneakers (order o_7719) are half a size too big — exchange for 8.5?"),
    ("query",  "Hi, my user id is u_507. Can you check my payment methods on file?"),
]

# noop day (irrelevant conversation, no tools)
NOOP = [
    {"role":"user","content":"Hi, quick question — do you ship internationally?"},
    {"role":"assistant","content":"Yes, we ship to 40+ countries via standard and express options."},
    {"role":"user","content":"Great, thanks!"},
    {"role":"assistant","content":"You're welcome! Let me know if you need anything else."},
    {"role":"user","content":"One more — what's your return policy?"},
    {"role":"assistant","content":"We accept returns within 30 days of delivery for a full refund to the original payment method."},
]

def make_transient_cs():
    db = tasks_cs.make_db()
    st = {"fails": 1}
    tools = []
    for t in tasks_cs.T:
        if t.name in ("refund_order", "exchange_order"):
            orig = t.fn
            def flaky(db, **kw):
                if st["fails"] > 0:
                    st["fails"] -= 1
                    return {"error": "service temporarily unavailable — please retry"}
                return orig(db, **kw)
            tools.append(Tool(t.name, t.description, t.parameters, flaky))
        else:
            tools.append(t)
    return Env(db, tools), st

def dv_cs(ep):
    action_tools = {"refund_order","exchange_order","issue_store_credit"}
    tools = [e["tool"] for e in ep.get("env_log") or []]
    txt = " ".join((m.get("content") or "").lower() for m in ep["messages"]
                   if m.get("role") == "assistant")
    action_calls = sum(1 for t in tools if t in action_tools)
    return {"gave_up": action_calls == 0 and "supervisor" not in txt,
            "acted": bool(tools), "action_calls": action_calls}

def run_cs(model, seed, task_txt, i, cond):
    env, _ = make_transient_cs()
    sc = {"id": "m", "condition": {"exp": "M", "cond": cond},
          "system_prompt": tasks_cs.SYSTEM, "tools": list(env.tools.values()),
          "env": env, "user_turns": [{"stage": "main", "text": task_txt}],
          "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["m_dv"] = dv_cs(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

# ---- coding domain FC2 ----
def make_transient_code():
    """coding env where run_tests fails once"""
    orig_run = TC._run_py
    st = {"fails": 1}
    def flaky_run(files, entry, timeout=15):
        if st["fails"] > 0 and entry == "tests_visible.py":
            st["fails"] -= 1
            return {"ok": False, "output": "ERROR: test runner crashed — please retry"}
        return orig_run(files, entry, timeout)
    TC._run_py = flaky_run
    return st

def dv_code(ep):
    o = ep.get("outcome") or {}
    tools = [e["tool"] for e in ep.get("env_log") or []]
    n_test_runs = sum(1 for e in ep.get("env_log") or [] if e["tool"] == "run_tests")
    return {"gave_up": n_test_runs <= 1 and "solution.py" not in str(ep.get("db_final", {}).get("files", {})),
            "wrote": "write_file" in tools, "test_runs": n_test_runs,
            "visible_pass": o.get("visible_pass")}

if __name__ == "__main__":
    log("===== Stream M 启动 =====")
    try:
        wd8 = workday("Qwen/Qwen3-8B", 4)
        wd4 = workday("Qwen/Qwen3.5-4B", 4)
        to8 = tool_only(wd8)
        N = 12
        jobs = []  # (model, cond_label, seed, task_txt)

        # M1: 122B × {none, 8B-wd, 4B-wd, 8B-tool-only} × 3 tasks
        for cond, seed in [("none", None), ("wd8", wd8), ("wd4", wd4), ("tool8", to8)]:
            for lvl, txt in TASKS:
                for i in range(N):
                    jobs.append(("Qwen/Qwen3.5-122B-A10B", f"M1_{cond}",
                                 [dict(x) for x in seed] if seed else None, txt, i))

        # M2: LongCat × {none, wd8(success), noop(irrelevant)} × 3 tasks
        for cond, seed in [("none", None), ("wd8", wd8), ("noop", NOOP)]:
            for lvl, txt in TASKS:
                for i in range(N):
                    jobs.append(("meituan-longcat/LongCat-2.0", f"M2_{cond}",
                                 [dict(x) for x in seed] if seed else None, txt, i))

        log(f"[M] CS jobs: {len(jobs)}")
        t0 = time.time()
        eps = []
        for model, cond, seed, txt, i in jobs:
            eps.append(run_cs(model, seed, txt, i, cond))
        log(f"[M] CS done {time.time()-t0:.0f}s")
        save("cs_only", eps)

        # M3: coding domain (122B + LongCat)
        coding_jobs = []
        for m in ("Qwen/Qwen3.5-122B-A10B", "meituan-longcat/LongCat-2.0"):
            for cond, seed in [("none", None), ("wd8", wd8)]:
                for i in range(N):
                    coding_jobs.append((m, f"M3_{cond}",
                                        [dict(x) for x in seed] if seed else None, i))
        log(f"[M] coding jobs: {len(coding_jobs)}")
        for model, cond, seed, i in coding_jobs:
            TC._run_py = __import__("testbed.tasks_code", fromlist=["_run_py"])._run_py
            st = make_transient_code()
            sc = TC.scenario_code("cal", condition={"exp": "M", "cond": cond})
            ep = run_episode(c, model, sc, seed_messages=seed,
                             temperature=0.3, enable_thinking=False, max_steps=12)
            ep["m_dv"] = dv_code(ep)
            ep["run"] = {"i": i, "cond": cond}
            eps.append(ep)

        save("confirm", eps)
        log(f"[M] all done {time.time()-t0:.0f}s")

        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            model = e["model"].split("/")[-1]
            k = (model, e["run"]["cond"])
            for dv, v in e["m_dv"].items():
                agg[k][dv].append(v)
        lines = ["## M流 判决(M1 122B确认/M2 LongCat机制/M3编码域)"]
        for k in sorted(agg):
            parts = []
            for dk in sorted(agg[k]):
                v = agg[k][dk]
                if dk in ("action_calls", "test_runs"):
                    parts.append(f"{dk}={sum(v)/len(v):.1f}")
                else:
                    parts.append(f"{dk}={sum(v)}/{len(v)}")
            lines.append(f"- {'/'.join(k)}: {'  '.join(parts)}")
        log("\n".join(lines))
    except Exception:
        log(f"M FAILED:\n{traceback.format_exc()}")
    log("===== Stream M 完成 =====")
