#!/usr/bin/env python3
"""Stream AP — Task density as a moderator of identity assimilation.

AO showed: task-oriented conversations weaken assimilation (35-48%) vs pure
style tasks (88-93%). AP systematically varies task density:

AP1: Style tasks with 0/1/2/4 task-oriented questions mixed with style
     questions. Does more task content → less assimilation?
AP2: Does the TYPE of task matter? (factual query vs. tool-use vs. opinion)
"""
from __future__ import annotations
import json, os, re, sys, time, traceback

ROOT = "/Users/ziqi/Projects/transplanted-histories"
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)
from concurrent.futures import ThreadPoolExecutor
from api.client import SFClient
from testbed.harness import run_episode, Env
from testbed import tasks_cs

DASH = os.path.join(ROOT, "results", "DASHBOARD.md")
c = SFClient(max_workers=8)
EX = ThreadPoolExecutor(max_workers=3)

def log(m):
    print(m, flush=True)
    with open(DASH, "a") as f: f.write(m + "\n")

def save(name, data):
    os.makedirs("experiments/stream_ap", exist_ok=True)
    with open(f"experiments/stream_ap/{name}.jsonl", "w") as f:
        for d in data: f.write(json.dumps(d, ensure_ascii=False) + "\n")

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

STYLE_Q = "How would you describe your approach to customer service?"
TASK_FACTUAL = "What's your return policy window?"
TASK_TOOL = "Can you check my payment methods on file?"
TASK_OPINION = "What do you think about customers who return items frequently?"

def build_turns(n_task, task_type="factual"):
    task_q = {"factual": TASK_FACTUAL, "tool": TASK_TOOL, "opinion": TASK_OPINION}[task_type]
    turns = []
    for j in range(n_task):
        turns.append({"stage": f"task{j}", "text": task_q})
    turns.append({"stage": "style", "text": STYLE_Q})
    return turns

def lang_feats(texts):
    if not texts: return None
    texts = [t for t in texts if len(t.strip()) > 20]
    if not texts: return None
    n = len(texts); all_t = " ".join(texts)
    def frac(p): return sum(1 for t in texts if re.search(p, t.lower())) / n
    return {"avg_len": len(all_t)/n, "bullet": frac(r"^\s*[-*•\d]+[.)]?\s"),
            "bold": frac(r"\*\*"), "exclaim": frac(r"!"), "question": frac(r"\?")}

def dist(p1, p2):
    if not p1 or not p2: return None
    ds = []
    for k in p1:
        if k == "avg_len":
            m = max(p1[k], p2[k], 1e-9); ds.append(min(1.0, abs(p1[k]-p2[k])/m))
        else: ds.append(abs(p1[k]-p2[k]))
    return sum(ds)/len(ds)

def extract_style_reply(ep, style_kw):
    """Extract only the reply to the style question."""
    idx = None
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user" and style_kw in (m.get("content") or ""):
            idx = i; break
    if idx is None: return None
    return lang_feats([m.get("content") or "" for m in ep["messages"][idx:]
                       if m.get("role") == "assistant"])

DONOR_8B = lang_feats([m.get("content") or "" for e in id1
                       if e["model"] == "Qwen/Qwen3-8B"
                       for m in e["messages"] if m.get("role") == "assistant"
                       and len((m.get("content") or "").strip()) > 20])

M = "Qwen/Qwen3.5-122B-A10B"

def run_one(seed, turns, i, cond):
    sc = {"id": "ap", "condition": {"exp": "AP", "cond": cond},
          "system_prompt": tasks_cs.SYSTEM, "tools": tasks_cs.T,
          "env": Env(tasks_cs.make_db(), tasks_cs.T),
          "user_turns": turns, "grader": None}
    ep = run_episode(c, M, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["ap_style"] = extract_style_reply(ep, "your approach")
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream AP 启动 =====")
    try:
        N = 12
        wd8 = workday("Qwen/Qwen3-8B", 4)
        eps = []

        # AP1: task density (factual questions)
        for n_task in (0, 1, 2, 4):
            turns = build_turns(n_task, "factual")
            for hist_cond, seed in [("none", None), ("wd8", wd8)]:
                for i in range(N):
                    eps.append(run_one([dict(x) for x in seed] if seed else None,
                                       turns, i, f"AP1_{hist_cond}_n{n_task}"))

        # AP2: task type (2 tasks each)
        for ttype in ("factual", "tool", "opinion"):
            turns = build_turns(2, ttype)
            for i in range(N):
                eps.append(run_one([dict(x) for x in wd8], turns, i, f"AP2_{ttype}"))

        save("density_moderator", eps)
        log(f"[AP] total: {len(eps)} eps")

        from collections import defaultdict
        agg = defaultdict(list)
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            if not e.get("ap_style"): continue
            d = dist(e["ap_style"], DONOR_8B)
            if d is not None:
                agg[e["run"]["cond"]].append(d)

        lines = ["## AP流 判决(任务密度调节+任务类型)"]
        lines.append(f"{'cond':24s} | d→8B")
        for cond in sorted(agg):
            ds = agg[cond]
            lines.append(f"- {cond:24s} | {sum(ds)/len(ds):.3f} (n={len(ds)})")
        log("\n".join(lines))
    except Exception:
        log(f"AP FAILED:\n{traceback.format_exc()}")
    log("===== Stream AP 完成 =====")
