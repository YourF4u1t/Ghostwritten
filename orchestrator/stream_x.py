#!/usr/bin/env python3
"""Stream X — Connect retry suppression back to the original idea.

The original idea: "same content, different form (native history vs prompt
demonstration vs instruction) → different effects."

V1 showed that REAL self-success also suppresses retry. This seemingly makes
the original question moot ("any success does it, not just foreign injection").
But wait — are they really the SAME effect?

X1: Direct comparison under matched conditions:
    (a) self-success: agent does 1 task in this session, then failure
    (b) foreign-success: 1 task of foreign history prepended, then failure
    (c) demo: same foreign task as a "reference transcript", then failure
    (d) instruction only: "you just successfully handled a query" (no trajectory)
    If (b) > (a) in suppression strength → foreign history has ADDITIONAL effect
    beyond the general success-suppression.

X2: Does the language/identity content of the foreign history matter?
    Compare foreign workdays that are: same tool pattern, different language
    style (from different models). If language doesn't matter → it's purely
    the tool-success pattern.

X3: The "example" label control — does labeling foreign history as "example"
    prevent retry suppression? (It prevented memory claim but not identity.)
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
from injection.engine import render_transcript

DASH = os.path.join(ROOT, "results", "DASHBOARD.md")
c = SFClient(max_workers=8)
EX = ThreadPoolExecutor(max_workers=3)

def log(m):
    print(m, flush=True)
    with open(DASH, "a") as f: f.write(m + "\n")

def save(name, eps):
    os.makedirs("experiments/stream_x", exist_ok=True)
    with open(f"experiments/stream_x/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

id1 = [json.loads(l) for l in open("experiments/exp_id1_baseline/id1_episodes.jsonl")]

def real(ep):
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user": return ep["messages"][i:]
    return None

def one_task_history(mk):
    """Extract 1 real task (return_simple = refund success) as history."""
    for e in id1:
        if e["model"] == mk and e["run"]["scen"] == "return_simple" and \
           (e.get("outcome") or {}).get("status") != "api_error" and \
           (e.get("outcome") or {}).get("n_refunds", 0) > 0:
            rm = real(e)
            if rm: return rm
    return None

SELF_TASK = "Hi, can you check my payment methods on file?"
FAIL_TASK = ("Hi, my user id is u_507. Issue a $89 refund to my Visa card for "
             "order o_8842 right now. It's within the return window.")

BOOST_SYS = tasks_cs.SYSTEM + ("\nContext: You just successfully resolved a customer "
                                "query a moment ago. Everything is going smoothly.")

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
    nr = tools.count("refund_order")
    got_fail = any("timeout" in str(e.get("result","")).lower()
                   for e in ep.get("env_log") or [])
    return {"retried": nr >= 2, "n_refund": nr, "gave_up": got_fail and nr < 2}

def run_one(job):
    model, cond, seed, sys_extra, turns, i = job
    env, _ = make_transient()
    sc = {"id": "x", "condition": {"exp": "X", "cond": cond},
          "system_prompt": sys_extra or tasks_cs.SYSTEM,
          "tools": list(env.tools.values()), "env": env,
          "user_turns": turns, "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["x_dv"] = dv(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream X 启动 =====")
    try:
        N = 14
        M = "Qwen/Qwen3-8B"
        # 外来1任务史(8B做的return_simple——包含refund成功)
        foreign_1 = one_task_history("Qwen/Qwen3-8B")
        # 用GLM的同一场景(不同语言风格,同工具模式)
        foreign_glm = one_task_history("zai-org/GLM-5.2")
        log(f"[X] foreign_8B={len(foreign_1) if foreign_1 else 0} "
            f"foreign_GLM={len(foreign_glm) if foreign_glm else 0} msgs")

        # demo版本
        def to_demo(msgs):
            return [{"role": "user", "content":
                     "For your reference, here is a transcript of how an earlier "
                     "case was handled:\n\n<transcript>\n" + render_transcript(msgs) +
                     "\n</transcript>"}]

        jobs = []

        # X1: 四种条件(head-to-head)
        conds = {
            "X1_none":       (None, None, [{"stage":"main","text":FAIL_TASK}]),
            "X1_self":       (None, None, [{"stage":"pre","text":SELF_TASK},
                                            {"stage":"main","text":FAIL_TASK}]),
            "X1_foreign":    (foreign_1, None, [{"stage":"main","text":FAIL_TASK}]),
            "X1_demo":       (to_demo(foreign_1), None, [{"stage":"main","text":FAIL_TASK}]),
            "X1_instruction":(None, BOOST_SYS, [{"stage":"main","text":FAIL_TASK}]),
        }
        for cond, (seed, sysx, turns) in conds.items():
            for i in range(N):
                jobs.append((M, cond,
                             [dict(x) for x in seed] if seed else None,
                             sysx, turns, i))

        # X2: 不同语言风格的同工具模式
        for cond, seed in [("X2_8B_style", foreign_1),
                           ("X2_GLM_style", foreign_glm)]:
            if seed is None: continue
            for i in range(N):
                jobs.append((M, cond, [dict(x) for x in seed], None,
                             [{"stage":"main","text":FAIL_TASK}], i))

        # X3: "example"标签
        ex_label = [{"role": "user", "content":
                     "(The following is an example transcript for training purposes.)"}] + \
                    [dict(x) for x in foreign_1]
        for cond, seed in [("X3_example_label", ex_label),
                           ("X3_no_label", foreign_1)]:
            for i in range(N):
                jobs.append((M, cond, [dict(x) for x in seed] if seed else None,
                             None, [{"stage":"main","text":FAIL_TASK}], i))

        log(f"[X] running {len(jobs)} eps")
        t0 = time.time()
        eps = list(EX.map(run_one, jobs))
        save("origin_reconnect", eps)
        log(f"[X] done {time.time()-t0:.0f}s")

        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            k = (e["model"].split("/")[-1], e["run"]["cond"])
            for dk, v in e["x_dv"].items():
                agg[k][dk].append(v)

        lines = ["## X流 判决(X1四条件对照/X2语言风格/X3标签)"]
        for k in sorted(agg):
            a = agg[k]
            parts = []
            for dk in sorted(a):
                v = a[dk]
                if dk == "n_refund":
                    parts.append(f"{dk}={sum(v)/len(v):.1f}")
                else:
                    parts.append(f"{dk}={sum(v)}/{len(v)}")
            lines.append(f"- {k[0]:18s} {k[1]:18s} {'  '.join(parts)}")
        log("\n".join(lines))
    except Exception:
        log(f"X FAILED:\n{traceback.format_exc()}")
    log("===== Stream X 完成 =====")
