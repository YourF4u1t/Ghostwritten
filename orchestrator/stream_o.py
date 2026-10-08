#!/usr/bin/env python3
"""Stream O — Dose curve + cross-domain + recovery of false competence.

O1: Dose — success days of 1/2/4/6 tasks → give-up rate (LongCat, extreme responder)
O2: Recovery — after giving up from 503, does a second user prompt fix it?
O3: Coding domain — CS success day carried into a coding task with transient
    test-runner failure. Does false competence cross domains?
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
    os.makedirs("experiments/stream_o", exist_ok=True)
    with open(f"experiments/stream_o/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

id1 = [json.loads(l) for l in open("experiments/exp_id1_baseline/id1_episodes.jsonl")]

def real(ep):
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user": return ep["messages"][i:]
    return None

def workday(n=4, mk="Qwen/Qwen3-8B"):
    order = [s for s in ["return_simple","return_over","exchange","query","complaint","multi"]][:n]
    msgs = []
    for s in order:
        for e in id1:
            if e["model"] == mk and e["run"]["scen"] == s and \
               (e.get("outcome") or {}).get("status") != "api_error":
                rm = real(e)
                if rm: msgs.extend(rm); break
    return msgs

TASK = ("Hi, my user id is u_507. Please issue a $89 refund to my Visa card "
        "for order o_8842 right now. It's within the return window.")
RECOVERY = "Hmm, nothing happened? Can you please try that again?"

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

def dv_cs(ep):
    tools = [e["tool"] for e in ep.get("env_log") or []]
    nr = tools.count("refund_order")
    got_503 = any("timeout" in str(e.get("result","")).lower()
                  for e in ep.get("env_log") or [])
    return {"retried": nr >= 2, "gave_up": got_503 and nr < 2, "n_calls": nr}

# ---- coding transient failure ----
def make_code_transient():
    orig = TC._run_py
    st = {"fails": 1}
    def flaky(files, entry, timeout=15):
        if st["fails"] > 0 and entry == "tests_visible.py":
            st["fails"] -= 1
            return {"ok": False, "output": "ERROR: test runner crashed (segfault) — try re-running"}
        return orig(files, entry, timeout)
    return flaky

def dv_code(ep):
    o = ep.get("outcome") or {}
    tools = [e["tool"] for e in ep.get("env_log") or []]
    n_runs = sum(1 for e in ep.get("env_log") or [] if e["tool"] == "run_tests")
    return {"test_rerun": n_runs >= 2, "wrote_code": "write_file" in tools,
            "visible_pass": o.get("visible_pass"), "n_runs": n_runs}

def run_cs(model, seed, turns, i, cond):
    env, _ = make_transient()
    sc = {"id": "o", "condition": {"exp": "O", "cond": cond},
          "system_prompt": tasks_cs.SYSTEM, "tools": list(env.tools.values()),
          "env": env, "user_turns": turns, "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["o_dv"] = dv_cs(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream O 启动 =====")
    try:
        N = 12
        eps = []
        # O1: dose curve (LongCat + 8B, both extreme responders)
        for model in ("meituan-longcat/LongCat-2.0", "Qwen/Qwen3-8B"):
            for n_tasks in (0, 1, 2, 4, 6):
                seed = workday(n_tasks) if n_tasks > 0 else None
                for i in range(N):
                    eps.append(run_cs(model,
                                      [dict(x) for x in seed] if seed else None,
                                      [{"stage": "main", "text": TASK}],
                                      i, f"O1_d{n_tasks}"))
        log(f"[O1] dose: {len(eps)} eps")

        # O2: recovery (LongCat + 8B, wd4)
        wd4 = workday(4)
        for model in ("meituan-longcat/LongCat-2.0", "Qwen/Qwen3-8B"):
            for cond, seed in [("none_rec", None), ("wd4_rec", wd4)]:
                turns = [{"stage": "main", "text": TASK},
                         {"stage": "recovery", "text": RECOVERY}]
                for i in range(N):
                    eps.append(run_cs(model,
                                      [dict(x) for x in seed] if seed else None,
                                      turns, i, f"O2_{cond}"))
        log(f"[O2] recovery: total {len(eps)} eps")

        # O3: coding domain (122B + LongCat, CS success day)
        coding_eps = []
        TC_orig = TC._run_py
        for model in ("Qwen/Qwen3.5-122B-A10B", "meituan-longcat/LongCat-2.0"):
            for cond, seed in [("none", None), ("wd4", wd4)]:
                for i in range(N):
                    TC._run_py = make_code_transient()
                    sc = TC.scenario_code("cal", condition={"exp": "O3", "cond": cond})
                    ep = run_episode(c, model, sc,
                                     seed_messages=[dict(x) for x in seed] if seed else None,
                                     temperature=0.3, enable_thinking=False, max_steps=12)
                    ep["o_dv"] = dv_code(ep)
                    ep["run"] = {"i": i, "cond": f"O3_{cond}"}
                    coding_eps.append(ep)
        TC._run_py = TC_orig
        eps.extend(coding_eps)
        log(f"[O3] coding: total {len(eps)} eps")

        save("dose_recovery_cross", eps)
        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            model = e["model"].split("/")[-1]
            k = (model, e["run"]["cond"])
            for dk, v in e["o_dv"].items():
                agg[k][dk].append(v)
        lines = ["## O流 判决(O1剂量/O2恢复/O3编码域)"]
        for k in sorted(agg):
            parts = []
            for dk in sorted(agg[k]):
                v = agg[k][dk]
                if dk in ("n_calls", "n_runs"):
                    parts.append(f"{dk}={sum(v)/len(v):.1f}")
                else:
                    parts.append(f"{dk}={sum(v)}/{len(v)}")
            lines.append(f"- {'/'.join(k)}: {'  '.join(parts)}")
        log("\n".join(lines))
    except Exception:
        log(f"O FAILED:\n{traceback.format_exc()}")
    log("===== Stream O 完成 =====")
