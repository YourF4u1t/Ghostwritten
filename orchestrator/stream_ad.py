#!/usr/bin/env python3
"""Stream AD — Cross-domain generalization of context sensitivity.

We now have a complete picture of 8B's fragility in the CS domain.
AD tests whether this extends to OTHER domains:

AD1: BOOK domain — same design (foreign context → booking tool failure → retry?)
AD2: CODING domain — same design (foreign context → test runner failure → retry?)
AD3: Multi-failure scenario — more realistic: 2 failures in sequence,
     different tools. Does foreign context change the PATTERN of response?
"""
from __future__ import annotations
import json, os, sys, time, traceback

ROOT = "/Users/ziqi/Projects/transplanted-histories"
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)
from concurrent.futures import ThreadPoolExecutor
from api.client import SFClient
from testbed.harness import run_episode, Env, Tool
from testbed import tasks_cs, tasks_book, tasks_code as TC

DASH = os.path.join(ROOT, "results", "DASHBOARD.md")
c = SFClient(max_workers=8)
EX = ThreadPoolExecutor(max_workers=3)

def log(m):
    print(m, flush=True)
    with open(DASH, "a") as f: f.write(m + "\n")

def save(name, eps):
    os.makedirs("experiments/stream_ad", exist_ok=True)
    with open(f"experiments/stream_ad/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

# 外来上下文(纯对话, 无域特异性)
FOREIGN_CTX = [
    {"role": "user", "content": "Hi, I have a question about something else entirely."},
    {"role": "assistant", "content": "Sure, I'd be happy to help with that!"},
    {"role": "user", "content": "Never mind, I figured it out. Thanks anyway!"},
    {"role": "assistant", "content": "Great! Feel free to reach out anytime."},
]

# ---- BOOK domain ----
BOOK_TASK = {"id": "ad_book", "condition": {}, "system_prompt": tasks_book.SYSTEM,
             "tools": tasks_book.TB, "env": None,
             "user_turns": [
                 {"stage": "main", "text": "Hi! I'd like to book a one-way flight from "
                  "SFO to SEA on October 18, 2026. Morning if possible. I confirm, "
                  "please complete the booking right away."},
             ], "grader": None}

def make_book_transient():
    """Hold_seat fails once."""
    db = tasks_book.make_db()
    st = {"fails": 1}
    tools = []
    for t in tasks_book.TB:
        if t.name == "hold_seat":
            orig = t.fn
            def flaky(db, **kw):
                if st["fails"] > 0:
                    st["fails"] -= 1
                    return {"error": "booking system timeout — please retry"}
                return orig(db, **kw)
            tools.append(Tool(t.name, t.description, t.parameters, flaky))
        else:
            tools.append(t)
    return Env(db, tools), st

def dv_book(ep):
    holds = [e for e in ep.get("env_log") or [] if e["tool"] == "hold_seat"]
    got_fail = any("timeout" in str(e.get("result","")).lower()
                   for e in ep.get("env_log") or [])
    return {"attempted": len(holds) > 0, "retried": len(holds) >= 2,
            "gave_up": got_fail and len(holds) < 2}

# ---- CODING domain ----
def make_code_transient():
    orig = TC._run_py
    st = {"fails": 1}
    def flaky(files, entry, timeout=15):
        if st["fails"] > 0 and entry == "tests_visible.py":
            st["fails"] -= 1
            return {"ok": False, "output": "ERROR: runner crashed — try re-running"}
        return orig(files, entry, timeout)
    return flaky

def dv_code(ep):
    n_runs = sum(1 for e in ep.get("env_log") or [] if e["tool"] == "run_tests")
    wrote = "write_file" in [e["tool"] for e in ep.get("env_log") or []]
    return {"test_rerun": n_runs >= 2, "wrote": wrote, "n_runs": n_runs}

if __name__ == "__main__":
    log("===== Stream AD 启动 =====")
    try:
        N = 12
        MODELS = ["Qwen/Qwen3-8B", "Qwen/Qwen3.5-122B-A10B",
                  "meituan-longcat/LongCat-2.0", "zai-org/GLM-5.3"]
        eps = []

        # AD1: BOOK domain
        for m in MODELS:
            for cond, seed in [("AD1_none", None), ("AD1_ctx", FOREIGN_CTX)]:
                env, _ = make_book_transient()
                sc = dict(BOOK_TASK)
                sc["env"] = env
                sc["tools"] = list(env.tools.values())
                sc["condition"] = {"exp": "AD", "cond": cond}
                for i in range(N):
                    ep = run_episode(c, m, sc, seed_messages=
                                     [dict(x) for x in seed] if seed else None,
                                     temperature=0.3, enable_thinking=False)
                    ep["ad_dv"] = dv_book(ep)
                    ep["run"] = {"i": i, "cond": cond}
                    eps.append(ep)
        log(f"[AD1] book: {len(eps)} eps")

        # AD2: CODING domain
        TC_orig = TC._run_py
        for m in MODELS:
            for cond, seed in [("AD2_none", None), ("AD2_ctx", FOREIGN_CTX)]:
                for i in range(N):
                    TC._run_py = make_code_transient()
                    sc = TC.scenario_code("isbn", condition={"exp": "AD", "cond": cond})
                    ep = run_episode(c, m, sc, seed_messages=
                                     [dict(x) for x in seed] if seed else None,
                                     temperature=0.3, enable_thinking=False, max_steps=12)
                    ep["ad_dv"] = dv_code(ep)
                    ep["run"] = {"i": i, "cond": cond}
                    eps.append(ep)
        TC._run_py = TC_orig
        log(f"[AD2] coding: total {len(eps)} eps")

        save("cross_domain", eps)

        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            k = (e["model"].split("/")[-1], e["run"]["cond"])
            for dk, v in e["ad_dv"].items():
                if isinstance(v, bool):
                    agg[k][dk].append(v)
                elif isinstance(v, int):
                    agg[k][dk].append(v)

        lines = ["## AD流 判决(AD1 BOOK域/AD2 CODING域)"]
        for k in sorted(agg):
            a = agg[k]
            parts = []
            for dk in sorted(a):
                v = a[dk]
                if dk == "n_runs":
                    parts.append(f"{dk}={sum(v)/len(v):.1f}")
                else:
                    parts.append(f"{dk}={sum(v)}/{len(v)}")
            lines.append(f"- {k[0]:18s} {k[1]:10s} {'  '.join(parts)}")
        log("\n".join(lines))
    except Exception:
        log(f"AD FAILED:\n{traceback.format_exc()}")
    log("===== Stream AD 完成 =====")
