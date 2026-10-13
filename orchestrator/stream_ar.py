#!/usr/bin/env python3
"""Stream AR — Within-session decay curve of identity assimilation.

AQ showed: all_msgs=88-90%, last_msg=10-12%. AR maps the full curve:
reply #1, #2, #3, #4, #5... each measured separately.

AR1: 8 sequential user questions (not task-oriented, just conversational).
     Measure d→donor for each reply position.
AR2: Same but with task-oriented questions (does task content slow decay?).
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

CONVO_QS = [
    "Hi! How does your return policy work?",
    "What happens if I return something without a receipt?",
    "Do you offer store credit as an alternative?",
    "How long does a refund take to process?",
    "What about items that arrive damaged?",
    "Is there a time limit on exchanges?",
    "Can I return gift items?",
    "One more thing — how would you describe your customer service philosophy?",
]

TASK_QS = [
    "Hi, check my payment methods on file.",
    "Now check order o_8842 for me.",
    "What's the status of order o_7719?",
    "Can you look up user u_507?",
    "Check order o_6102 too.",
    "What payment methods do I have?",
    "Look up order o_6590.",
    "Finally, how would you describe your customer service philosophy?",
]

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

def extract_by_position(ep):
    """Return list of (position, d→donor) for each assistant reply."""
    replies = []
    reply_idx = 0
    for m in ep["messages"]:
        if m.get("role") == "assistant" and m.get("content") and len(m["content"].strip()) > 20:
            f = lang_feats([m["content"]])
            d = dist(f, DONOR_8B) if f else None
            replies.append((reply_idx, d))
            reply_idx += 1
    return replies

if __name__ == "__main__":
    log("===== Stream AR 启动 =====")
    try:
        N = 10
        wd8 = workday("Qwen/Qwen3-8B", 4)
        results = []

        for cond, questions, seed in [
            ("AR1_convo_wd8", CONVO_QS, wd8),
            ("AR1_convo_none", CONVO_QS, None),
            ("AR2_task_wd8", TASK_QS, wd8),
        ]:
            for i in range(N):
                sc = {"id": "ar", "condition": {"exp": "AR", "cond": cond},
                      "system_prompt": tasks_cs.SYSTEM,
                      "tools": [], "env": Env({"files": {}, "runs": 0}, []),
                      "user_turns": [{"stage": f"q{j}", "text": q}
                                     for j, q in enumerate(questions)],
                      "grader": None}
                ep = run_episode(c, M, sc, seed_messages=
                                 [dict(x) for x in seed] if seed else None,
                                 temperature=0.3, enable_thinking=False)
                by_pos = extract_by_position(ep)
                for pos, d in by_pos:
                    results.append({"cond": cond, "run": i, "position": pos, "d": d})

        import os as _os; _os.makedirs("experiments/stream_ar", exist_ok=True)
        with open("experiments/stream_ar/decay_curve.jsonl", "w") as f:
            for r in results: f.write(json.dumps(r) + "\n")

        from collections import defaultdict
        agg = defaultdict(list)
        for r in results:
            if r["d"] is not None:
                agg[(r["cond"], r["position"])].append(r["d"])

        lines = ["## AR流 判决(会话内衰减曲线)"]
        lines.append(f"{'position':6s}", )
        # Build header
        conds = sorted(set(r["cond"] for r in results))
        header = f"{'pos':5s} | " + " | ".join(f"{c:16s}" for c in conds)
        lines.append(header)
        max_pos = max(r["position"] for r in results)
        for pos in range(min(max_pos, 8)):
            row = f"{pos:5d} | "
            for cond in conds:
                ds = agg.get((cond, pos), [])
                if ds:
                    row += f"{sum(ds)/len(ds):16.3f}"
                else:
                    row += f"{'—':>16s}"
            lines.append(row)
        log("\n".join(lines))
    except Exception:
        log(f"AR FAILED:\n{traceback.format_exc()}")
    log("===== Stream AR 完成 =====")
