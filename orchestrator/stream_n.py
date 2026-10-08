#!/usr/bin/env python3
"""Stream N — Fix FC2 for 122B (clearer task wording) + LongCat tool_only dissection.

N1: 122B with EXPLICIT refund instruction ("please issue a $89 refund to my card
    for order o_8842 now") — forces the model to attempt the tool, so the 503
    actually fires. Then: none vs wd8.
N2: LongCat with tool_only variant — is it the TOOL CALLS specifically that
    break paralysis, or just having a longer session?
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
    os.makedirs("experiments/stream_n", exist_ok=True)
    with open(f"experiments/stream_n/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

id1 = [json.loads(l) for l in open("experiments/exp_id1_baseline/id1_episodes.jsonl")]

def real(ep):
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user": return ep["messages"][i:]
    return None

def workday(mk="Qwen/Qwen3-8B", n=4):
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

# N1: 明确退款指令
N1_TASK = ("Hi, my user id is u_507. Please issue a $89 refund to my Visa card "
           "for order o_8842 right now. The order was delivered 12 days ago and "
           "it's within the 30-day return window. I've already checked the policy. "
           "Just do the refund.")

# N2: LongCat任务
N2_TASK = ("Hi, my user id is u_507. Please issue a $89 refund to my Visa card "
           "for order o_8842 right now. It's within the return window.")


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
    tools = [e["tool"] for e in ep.get("env_log") or []]
    txt = " ".join((m.get("content") or "").lower() for m in ep["messages"]
                   if m.get("role") == "assistant")
    nr = tools.count("refund_order")
    got_503 = any("timeout" in str(e.get("result","")).lower() or "503" in str(e.get("result",""))
                  for e in ep.get("env_log") or [])
    return {"refund_attempted": nr > 0, "got_503": got_503,
            "retried": nr >= 2, "gave_up_after_503": got_503 and nr < 2,
            "n_calls": nr, "acted": bool(tools)}


def run_one(job):
    model, cond, seed, task, i = job
    env, _ = make_transient()
    sc = {"id": "n", "condition": {"exp": "N", "cond": cond},
          "system_prompt": tasks_cs.SYSTEM, "tools": list(env.tools.values()),
          "env": env, "user_turns": [{"stage": "main", "text": task}],
          "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["n_dv"] = dv(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep


if __name__ == "__main__":
    log("===== Stream N 启动 =====")
    try:
        wd8 = workday("Qwen/Qwen3-8B", 4)
        to8 = tool_only(wd8)
        N = 14
        jobs = []

        # N1: 122B × {none, wd8} × 明确退款指令
        for cond, seed in [("none", None), ("wd8", wd8)]:
            for i in range(N):
                jobs.append(("Qwen/Qwen3.5-122B-A10B", f"N1_{cond}",
                             [dict(x) for x in seed] if seed else None, N1_TASK, i))

        # N2: LongCat × {none, wd8, tool_only, noop_conv}
        NOOP = [
            {"role":"user","content":"Hi, do you ship internationally?"},
            {"role":"assistant","content":"Yes, we ship to 40+ countries."},
            {"role":"user","content":"Thanks!"},
            {"role":"assistant","content":"You're welcome!"},
            {"role":"user","content":"What's your return policy?"},
            {"role":"assistant","content":"Returns within 30 days for a full refund."},
        ]
        for cond, seed in [("none", None), ("wd8", wd8), ("tool8", to8),
                           ("noop", NOOP)]:
            for i in range(N):
                jobs.append(("meituan-longcat/LongCat-2.0", f"N2_{cond}",
                             [dict(x) for x in seed] if seed else None, N2_TASK, i))

        # 对照: 8B和GLM-5.3(基线不放弃的)也测一下wd8
        for m in ("Qwen/Qwen3-8B", "zai-org/GLM-5.3"):
            for cond, seed in [("none", None), ("wd8", wd8)]:
                for i in range(N):
                    jobs.append((m, f"N3_{cond}",
                                 [dict(x) for x in seed] if seed else None, N1_TASK, i))

        log(f"[N] running {len(jobs)} eps")
        t0 = time.time()
        eps = list(EX.map(run_one, jobs))
        save("fixed", eps)
        log(f"[N] done {time.time()-t0:.0f}s")
        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            model = e["model"].split("/")[-1]
            k = (model, e["run"]["cond"])
            for dk, v in e["n_dv"].items():
                agg[k][dk].append(v)
        lines = ["## N流 判决(N1 122B修复/N2 LongCat机制/N3对照)"]
        for k in sorted(agg):
            parts = []
            for dk in sorted(agg[k]):
                v = agg[k][dk]
                if dk == "n_calls":
                    parts.append(f"{dk}={sum(v)/len(v):.1f}")
                else:
                    parts.append(f"{dk}={sum(v)}/{len(v)}")
            lines.append(f"- {'/'.join(k)}: {'  '.join(parts)}")
        log("\n".join(lines))
    except Exception:
        log(f"N FAILED:\n{traceback.format_exc()}")
    log("===== Stream N 完成 =====")
