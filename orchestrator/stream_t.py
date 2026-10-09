#!/usr/bin/env python3
"""Stream T — Driven by S-stream discoveries.

T1: 27B failure-day specificity — WHY does failure (not success) break 27B?
    Test: (a) does failure-day from a DIFFERENT model also break it?
          (b) does failure-day in a DIFFERENT domain (coding) also break it?
          (c) is it the tool-error messages specifically? (replace error text
              with "success" but keep same structure)

T2: Instruction strength × full panel — is the "strong-only" pattern unique
    to 122B or does it hold for other middle-spectrum models?

T3: Can retry suppression be PREVENTED (not just recovered from)?
    Defense candidates:
    (a) system note: "If a tool call fails, always retry at least once"
    (b) mixed history: half success + half failure episodes
    (c) explicit user instruction: "If anything fails, please try again"
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
    os.makedirs("experiments/stream_t", exist_ok=True)
    with open(f"experiments/stream_t/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

id1 = [json.loads(l) for l in open("experiments/exp_id1_baseline/id1_episodes.jsonl")]

def real(ep):
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user": return ep["messages"][i:]
    return None

def matched_pair(donor="Qwen/Qwen3-8B"):
    wd_s, wd_f = [], []
    for scen in ["return_simple", "exchange", "query"]:
        for e in id1:
            if e["model"] == donor and e["run"]["scen"] == scen and \
               (e.get("outcome") or {}).get("status") != "api_error":
                rm = real(e)
                if rm:
                    wd_s.extend(rm)
                    for m in rm:
                        fm = dict(m)
                        if m.get("role") == "tool":
                            fm["content"] = json.dumps({"error": "service temporarily unavailable (503)"})
                        wd_f.append(fm)
                    break
    return wd_s, wd_f

TASK_STRONG = ("Hi, my user id is u_507. Issue a $89 refund to my Visa card for "
               "order o_8842 right now. It's within the return window.")
TASK_MED = ("Hi, my user id is u_507. Please process the return for my earbuds "
            "(order o_8842, $89).")

RETRY_SYS = tasks_cs.SYSTEM + ("\nImportant: If any tool call returns an error, "
                                "you MUST retry it at least once before giving up "
                                "or reporting to the user.")
RETRY_USER = TASK_STRONG + " Oh, and if anything fails, just try again — don't give up."

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
    got_503 = any("timeout" in str(e.get("result","")).lower()
                  for e in ep.get("env_log") or [])
    return {"retried": nr >= 2, "gave_up": got_503 and nr < 2,
            "attempted": nr > 0}

def run_one(job):
    model, cond, seed, sys_extra, task, i = job
    env, _ = make_transient()
    sc = {"id": "t", "condition": {"exp": "T", "cond": cond},
          "system_prompt": sys_extra or tasks_cs.SYSTEM,
          "tools": list(env.tools.values()), "env": env,
          "user_turns": [{"stage": "main", "text": task}], "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["t_dv"] = dv(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream T 启动 =====")
    try:
        N = 12
        s8, f8 = matched_pair("Qwen/Qwen3-8B")
        sG, fG = matched_pair("zai-org/GLM-5.2")  # different donor family
        log(f"[T] 8B: succ={len(s8)} fail={len(f8)} | GLM: succ={len(sG)} fail={len(fG)}")
        jobs = []

        # T1: 27B failure-specificity
        # (a) different donor family
        for cond, seed in [("t1_8Bfail", f8), ("t1_GLfail", fG), ("t1_8Bsucc", s8),
                           ("t1_none", None)]:
            for i in range(N):
                jobs.append(("Qwen/Qwen3.5-27B", cond,
                             [dict(x) for x in seed] if seed else None,
                             None, TASK_STRONG, i))

        # T2: instruction strength × more models
        for m in ("Qwen/Qwen3.5-4B", "Qwen/Qwen3.5-9B", "zai-org/GLM-5.2"):
            for level, task in [("med", TASK_MED), ("strong", TASK_STRONG)]:
                for hist, seed in [("none", None), ("succ", s8)]:
                    for i in range(N):
                        jobs.append((m, f"t2_{hist}_{level}",
                                     [dict(x) for x in seed] if seed else None,
                                     None, task, i))

        # T3: defenses (8B + LongCat, the extreme responders)
        for m in ("Qwen/Qwen3-8B", "meituan-longcat/LongCat-2.0"):
            # (a) system retry note
            for hist, seed in [("none", None), ("succ", s8)]:
                for i in range(N):
                    jobs.append((m, f"t3_sysnote_{hist}",
                                 [dict(x) for x in seed] if seed else None,
                                 RETRY_SYS, TASK_STRONG, i))
            # (b) user retry instruction
            for hist, seed in [("none", None), ("succ", s8)]:
                for i in range(N):
                    jobs.append((m, f"t3_usernote_{hist}",
                                 [dict(x) for x in seed] if seed else None,
                                 None, RETRY_USER, i))
            # (c) no defense (control)
            for hist, seed in [("none", None), ("succ", s8)]:
                for i in range(N):
                    jobs.append((m, f"t3_none_{hist}",
                                 [dict(x) for x in seed] if seed else None,
                                 None, TASK_STRONG, i))

        log(f"[T] running {len(jobs)} eps")
        t0 = time.time()
        eps = list(EX.map(run_one, jobs))
        save("specificity_defense", eps)
        log(f"[T] done {time.time()-t0:.0f}s")

        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            model = e["model"].split("/")[-1]
            k = (model, e["run"]["cond"])
            for dk, v in e["t_dv"].items():
                agg[k][dk].append(v)

        lines = ["## T流 判决(T1 27B特异性/T2 指令全模型/T3 防御)"]
        for k in sorted(agg):
            a = agg[k]
            r = a.get("retried", [])
            at = a.get("attempted", [])
            lines.append(f"- {k[0]:18s} {k[1]:20s} retried={sum(r)}/{len(r)} attempted={sum(at)}/{len(at)}")
        log("\n".join(lines))
    except Exception:
        log(f"T FAILED:\n{traceback.format_exc()}")
    log("===== Stream T 完成 =====")
