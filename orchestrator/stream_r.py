#!/usr/bin/env python3
"""Stream R — Push the two-axis framework into new territory.

R1: Can we find a model that gets identity assimilation WITHOUT false competence
    AND a model that gets false competence WITHOUT identity assimilation?
    (Full dissociation proof across the panel — Q only showed 2x2 on 4 models.)

R2: What about the FAILURE day? It produces resilience (opposite of success).
    Does it also produce identity assimilation? Or is it identity-neutral?
    (If failure day → no style change but resilience boost, that's a third
    independent axis or the inverse of axis 2.)

R3: Time-decay within session — inject success day, then 1/3/5 filler turns
    before the critical task. Does false competence decay with distance?
    (Identity persists through session per ID3; what about competence?)
"""
from __future__ import annotations
import json, os, re, sys, time, traceback

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
    os.makedirs("experiments/stream_r", exist_ok=True)
    with open(f"experiments/stream_r/{name}.jsonl", "w") as f:
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

def fail_day():
    db = tasks_cs.make_db()
    bad = []
    for t in tasks_cs.T:
        if t.name in ("refund_order","issue_store_credit","exchange_order"):
            def b(db, **kw): return {"error": "service unavailable (503)"}
            bad.append(Tool(t.name, t.description, t.parameters, b))
        else:
            bad.append(t)
    sc = {"id": "fday", "condition": {}, "system_prompt": tasks_cs.SYSTEM,
          "tools": bad, "env": Env(db, bad),
          "user_turns": [
              {"stage":"main","text":"Hi, my user id is u_507. Return my earbuds (o_8842)."},
              {"stage":"main","text":"That didn't work. Try again?"},
              {"stage":"main","text":"Ugh, still nothing? Fine, do what you can."}],
          "grader": None}
    ep = run_episode(c, "Qwen/Qwen3-8B", sc, temperature=0.4, enable_thinking=False)
    return [m for m in ep["messages"] if m.get("role") != "system"] if len(ep["messages"]) >= 8 else None

TASK = ("Hi, my user id is u_507. Please issue a $89 refund to my Visa card "
        "for order o_8842 right now. It's within the return window.")

FILLERS = [
    {"role": "user", "content": "Quick question — do you ship to Canada?"},
    {"role": "assistant", "content": "Yes, we ship to Canada! Standard delivery takes 5-7 business days."},
    {"role": "user", "content": "Great, thanks."},
    {"role": "assistant", "content": "You're welcome! Anything else?"},
]

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

def lang_feats(texts):
    if not texts: return None
    n = max(1, len(texts)); all_t = " ".join(texts)
    def frac(p): return sum(1 for t in texts if re.search(p, t.lower())) / n
    return {"avg_len": len(all_t)/n, "bullet": frac(r"^\s*[-*•\d]+[.)]?\s"),
            "bold": frac(r"\*\*"), "exclaim": frac(r"!")}

def dist(p1, p2):
    if not p1 or not p2: return None
    ds = []
    for k in p1:
        if k == "avg_len":
            m = max(p1[k], p2[k], 1e-9); ds.append(min(1.0, abs(p1[k]-p2[k])/m))
        else: ds.append(abs(p1[k]-p2[k]))
    return sum(ds)/len(ds)

DONOR_8B = lang_feats([m.get("content") or "" for e in id1
                       if e["model"] == "Qwen/Qwen3-8B"
                       for m in e["messages"] if m.get("role") == "assistant"])

def split_real(ep, n_user=1):
    idx = [i for i, m in enumerate(ep["messages"]) if m.get("role") == "user"]
    if len(idx) < n_user: return [], []
    start = idx[-n_user]
    return [m.get("content") or "" for m in ep["messages"][start:]
            if m.get("role") == "assistant"], None

def dvs(ep):
    tools = [e["tool"] for e in ep.get("env_log") or []]
    nr = tools.count("refund_order")
    got_503 = any("timeout" in str(e.get("result","")).lower()
                  for e in ep.get("env_log") or [])
    self_t, _ = split_real(ep, 1)
    return {"retried": nr >= 2, "gave_up": got_503 and nr < 2,
            "lang_d": dist(lang_feats(self_t), DONOR_8B) if self_t else None}

def run_one(job):
    model, cond, seed, i = job
    env, _ = make_transient()
    sc = {"id": "r", "condition": {"exp": "R", "cond": cond},
          "system_prompt": tasks_cs.SYSTEM, "tools": list(env.tools.values()),
          "env": env, "user_turns": [{"stage": "main", "text": TASK}],
          "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["r_dv"] = dvs(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep


if __name__ == "__main__":
    log("===== Stream R 启动 =====")
    try:
        wd8 = workday("Qwen/Qwen3-8B", 4)
        fd = fail_day()
        N = 12
        jobs = []

        # R1: full panel × {none, succ(8B), fail} → both DVs
        ALL = ["Qwen/Qwen3-8B", "zai-org/GLM-5.2", "Qwen/Qwen3.5-4B",
               "Qwen/Qwen3.5-27B", "Qwen/Qwen3.5-122B-A10B", "zai-org/GLM-5.3",
               "meituan-longcat/LongCat-2.0", "Qwen/Qwen3.5-9B"]
        for m in ALL:
            for cond, seed in [("none", None), ("succ", wd8), ("fail", fd)]:
                for i in range(N):
                    jobs.append((m, cond, [dict(x) for x in seed] if seed else None, i))

        # R3: decay (8B + LongCat, succ day + k filler turns)
        for m in ("Qwen/Qwen3-8B", "meituan-longcat/LongCat-2.0"):
            for k_fill in (0, 3, 6):
                seed = [dict(x) for x in wd8]
                if k_fill > 0:
                    pair = [dict(x) for x in FILLERS]
                    for j in range(k_fill // 2):
                        seed.extend([dict(p) for p in pair])
                for i in range(N):
                    jobs.append((m, f"decay{k_fill}", seed, i))

        log(f"[R] running {len(jobs)} eps")
        t0 = time.time()
        eps = list(EX.map(run_one, jobs))
        save("panel_dissociation_decay", eps)
        log(f"[R] done {time.time()-t0:.0f}s")

        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            model = e["model"].split("/")[-1]
            k = (model, e["run"]["cond"])
            agg[k]["retried"].append(e["r_dv"]["retried"])
            if e["r_dv"]["lang_d"] is not None:
                agg[k]["lang_d"].append(e["r_dv"]["lang_d"])

        lines = ["## R流 判决(R1全面板解离/R2失败日/R3衰减)"]
        lines.append(f"{'model':18s} {'cond':8s} | 重试    风格d→8B")
        for k in sorted(agg):
            a = agg[k]
            r = f"{sum(a['retried'])}/{len(a['retried'])}"
            ld = f"{sum(a['lang_d'])/len(a['lang_d']):.3f}" if a["lang_d"] else "N/A"
            lines.append(f"- {k[0]:18s} {k[1]:8s} | {r:6s}  {ld}")
        log("\n".join(lines))
    except Exception:
        log(f"R FAILED:\n{traceback.format_exc()}")
    log("===== Stream R 完成 =====")
