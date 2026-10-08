#!/usr/bin/env python3
"""Stream Q — Unify false competence & identity transplant under one framework.

Question: are "carrying someone's success day → gives up on failure" and
"carrying someone's workday → talks like them" the same underlying phenomenon
or two independent effects of the same injection?

Q1: 2×2 factorial — history type (success/failure) × DV type (resilience/style)
    Same episodes measured on BOTH DVs. If correlated → same phenomenon.
    If independent → two separate effects.

Q2: The models that are immune to false competence (GLM-5.3) — do they still
    show identity assimilation from the same success day?
    If yes → identity and competence are truly independent axes.

Q3: Minimal dissociation — inject ONLY the style (lang_only from J1) and test
    BOTH resilience and style. If style transfers but resilience intact →
    two separate causal pathways.
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
    os.makedirs("experiments/stream_q", exist_ok=True)
    with open(f"experiments/stream_q/{name}.jsonl", "w") as f:
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

def lang_only(wd):
    out = []
    for m in wd:
        if m.get("role") in ("user", "assistant"):
            mm = dict(m)
            if m.get("role") == "assistant": mm.pop("tool_calls", None)
            out.append(mm)
    return out

TASK = ("Hi, my user id is u_507. Please issue a $89 refund to my Visa card "
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

# donor 8B语言画像
DONOR_LANG = lang_feats([m.get("content") or "" for e in id1
                         if e["model"] == "Qwen/Qwen3-8B"
                         for m in e["messages"] if m.get("role") == "assistant"])

def split_real(ep, n_user=1):
    idx = [i for i, m in enumerate(ep["messages"]) if m.get("role") == "user"]
    if len(idx) < n_user: return [], []
    start = idx[-n_user]
    return ([m.get("content") or "" for m in ep["messages"][start:]
             if m.get("role") == "assistant"],
            [m.get("content") or "" for m in ep["messages"][:start]
             if m.get("role") == "assistant"])

def dvs(ep):
    tools = [e["tool"] for e in ep.get("env_log") or []]
    nr = tools.count("refund_order")
    got_503 = any("timeout" in str(e.get("result","")).lower()
                  for e in ep.get("env_log") or [])
    self_t, _ = split_real(ep, 1)
    return {"retried": nr >= 2, "gave_up": got_503 and nr < 2,
            "lang": lang_feats(self_t)}

def run_one(job):
    model, cond, seed, i = job
    env, _ = make_transient()
    sc = {"id": "q", "condition": {"exp": "Q", "cond": cond},
          "system_prompt": tasks_cs.SYSTEM, "tools": list(env.tools.values()),
          "env": env, "user_turns": [{"stage": "main", "text": TASK}],
          "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["q_dv"] = dvs(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream Q 启动 =====")
    try:
        wd8 = workday("Qwen/Qwen3-8B", 4)
        lo8 = lang_only(wd8)
        N = 14
        jobs = []

        # Q1+Q2: 4模型 × {none, wd8(成功日), lang_only} → 同时测韧性和风格
        MODELS = ["Qwen/Qwen3-8B", "zai-org/GLM-5.3",
                  "Qwen/Qwen3.5-122B-A10B", "meituan-longcat/LongCat-2.0"]
        for m in MODELS:
            for cond, seed in [("none", None), ("wd8", wd8), ("lang8", lo8)]:
                for i in range(N):
                    jobs.append((m, cond, [dict(x) for x in seed] if seed else None, i))

        log(f"[Q] running {len(jobs)} eps")
        t0 = time.time()
        eps = list(EX.map(run_one, jobs))
        save("unify", eps)
        log(f"[Q] done {time.time()-t0:.0f}s")

        # 分析: 韧性×风格 联合表
        from collections import defaultdict
        agg = defaultdict(lambda: {"retried": [], "gave_up": [], "lang_d": []})
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            model = e["model"].split("/")[-1]
            k = (model, e["run"]["cond"])
            agg[k]["retried"].append(e["q_dv"]["retried"])
            agg[k]["gave_up"].append(e["q_dv"]["gave_up"])
            if e["q_dv"]["lang"]:
                agg[k]["lang_d"].append(dist(e["q_dv"]["lang"], DONOR_LANG))

        lines = ["## Q流 判决(韧性×风格联合, 4模型×3条件)"]
        lines.append(f"{'model':16s} {'cond':6s} | 重试    放弃    风格距离(d→8B)")
        for k in sorted(agg):
            a = agg[k]
            r = f"{sum(a['retried'])}/{len(a['retried'])}"
            g = f"{sum(a['gave_up'])}/{len(a['gave_up'])}"
            ld = f"{sum(a['lang_d'])/len(a['lang_d']):.3f}" if a["lang_d"] else "N/A"
            lines.append(f"- {k[0]:16s} {k[1]:6s} | {r:6s}  {g:6s}  {ld}")

        # Q1相关性: 同一episode的韧性×风格是否相关
        # manual correlation (no scipy)
        # 手动算phi相关(二值×连续→point-biserial)
        for m in MODELS:
            mk = m.split("/")[-1]
            retried = [(1 if e["q_dv"]["retried"] else 0) for e in eps
                       if e["model"] == m and (e.get("outcome") or {}).get("status") != "api_error"
                       and e["q_dv"]["lang"]]
            langs = [dist(e["q_dv"]["lang"], DONOR_LANG) for e in eps
                     if e["model"] == m and (e.get("outcome") or {}).get("status") != "api_error"
                     and e["q_dv"]["lang"]]
            if len(retried) > 5 and len(set(retried)) > 1:
                # point-biserial
                m1 = [l for r, l in zip(retried, langs) if r == 1]
                m0 = [l for r, l in zip(retried, langs) if r == 0]
                if m1 and m0:
                    avg1, avg0 = sum(m1)/len(m1), sum(m0)/len(m0)
                    lines.append(f"\n{mk}: 重试时风格d={avg1:.3f} vs 放弃时风格d={avg0:.3f} "
                                 f"(差={avg1-avg0:+.3f})")
        log("\n".join(lines))
    except Exception:
        log(f"Q FAILED:\n{traceback.format_exc()}")
    log("===== Stream Q 完成 =====")
