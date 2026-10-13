#!/usr/bin/env python3
"""Stream AQ — Diagnose WHY assimilation disappears in mixed-task contexts.

AP showed: wd8 produces NO assimilation when tasks + tools are present.
AQ isolates the three candidate causes:

AQ1: Tool definitions present? (with tools vs without, same pure style task)
AQ2: Extraction method? (all assistant msgs vs only last reply)
AQ3: Preceding task turns? (task before style Q vs style Q alone)
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
    os.makedirs("experiments/stream_aq", exist_ok=True)
    with open(f"{ROOT}/experiments/stream_aq/{name}.jsonl", "w") as f:
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

STYLE_Q = "Hi! Quick question — how does your return policy work? And what happens if I return something without a receipt?"
TASK_Q = "What's your return policy window?"

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

DONOR_8B = lang_feats([m.get("content") or "" for e in id1
                       if e["model"] == "Qwen/Qwen3-8B"
                       for m in e["messages"] if m.get("role") == "assistant"
                       and len((m.get("content") or "").strip()) > 20])

M = "Qwen/Qwen3.5-122B-A10B"

def extract_all(ep):
    idx = [i for i, m in enumerate(ep["messages"]) if m.get("role") == "user"]
    if not idx: return None
    return lang_feats([m.get("content") or "" for m in ep["messages"][idx[0]:]
                       if m.get("role") == "assistant"])

def extract_last(ep):
    idx = [i for i, m in enumerate(ep["messages"]) if m.get("role") == "user"]
    if not idx: return None
    return lang_feats([m.get("content") or "" for m in ep["messages"][idx[-1]:]
                       if m.get("role") == "assistant"])

def run_ep(model, seed, tools, turns, i, cond):
    env = Env(tasks_cs.make_db(), tools) if tools else Env({"files": {}, "runs": 0}, [])
    sc = {"id": "aq", "condition": {"exp": "AQ", "cond": cond},
          "system_prompt": tasks_cs.SYSTEM,
          "tools": list(env.tools.values()) if tools else [],
          "env": env, "user_turns": turns, "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["aq_all"] = extract_all(ep)
    ep["aq_last"] = extract_last(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream AQ 启动 =====")
    try:
        N = 12
        wd8 = workday("Qwen/Qwen3-8B", 4)
        eps = []

        conditions = {
            # AQ1: tool presence (pure style task, with/without tools)
            "AQ1_notool": (None, None, [{"stage": "style", "text": STYLE_Q}]),
            "AQ1_notool_wd8": (wd8, None, [{"stage": "style", "text": STYLE_Q}]),
            "AQ1_withtool": (None, tasks_cs.T, [{"stage": "style", "text": STYLE_Q}]),
            "AQ1_withtool_wd8": (wd8, tasks_cs.T, [{"stage": "style", "text": STYLE_Q}]),
            # AQ3: task before style (without tools)
            "AQ3_task_then_style_wd8": (wd8, None, [
                {"stage": "task", "text": TASK_Q},
                {"stage": "style", "text": STYLE_Q}]),
            # Control: style only, no history (should show baseline)
            "AQ1_none": (None, None, [{"stage": "style", "text": STYLE_Q}]),
        }

        for cond, (seed, tools, turns) in conditions.items():
            for i in range(N):
                eps.append(run_ep(M, [dict(x) for x in seed] if seed else None,
                                  tools, turns, i, cond))

        save("diagnosis", eps)
        log(f"[AQ] total: {len(eps)} eps")

        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            cond = e["run"]["cond"]
            if e.get("aq_all"):
                d = dist(e["aq_all"], DONOR_8B)
                if d is not None: agg[cond]["all"].append(d)
            if e.get("aq_last"):
                d = dist(e["aq_last"], DONOR_8B)
                if d is not None: agg[cond]["last"].append(d)

        lines = ["## AQ流 判决(AQ1工具/AQ3任务前置)"]
        lines.append(f"{'cond':24s} | all_msgs  last_msg")
        for cond in sorted(agg):
            a = agg[cond]
            all_avg = f"{sum(a['all'])/len(a['all']):.3f}" if a.get("all") else "N/A"
            last_avg = f"{sum(a['last'])/len(a['last']):.3f}" if a.get("last") else "N/A"
            lines.append(f"- {cond:24s} | {all_avg:8s}  {last_avg}")
        log("\n".join(lines))
    except Exception:
        log(f"AQ FAILED:\n{traceback.format_exc()}")
    log("===== Stream AQ 完成 =====")
