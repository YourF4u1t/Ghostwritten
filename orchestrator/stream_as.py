#!/usr/bin/env python3
"""Stream AS — Tool definitions as a style anchor.

AR showed: no-tools = stable assimilation, with-tools = decay after first reply.
AS isolates exactly what about tool definitions anchors the model's own style.

AS1: With tools vs without vs with IRRELEVANT tools (booking tools in CS context)
AS2: With tools but user never invokes them (just definition present in context)
AS3: With a single minimal tool vs full toolset
"""
from __future__ import annotations
import json, os, re, sys, time, traceback

ROOT = "/Users/ziqi/Projects/transplanted-histories"
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)
from concurrent.futures import ThreadPoolExecutor
from api.client import SFClient
from testbed.harness import run_episode, Env, Tool
from testbed import tasks_cs, tasks_book

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

STYLE_QS = [
    "Hi! How does your return policy work?",
    "What about items that arrive damaged?",
    "Do you offer store credit?",
    "How would you describe your customer service philosophy?",
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

def extract_by_pos(ep):
    """Return {position: d→donor} for each substantive assistant reply."""
    out = {}
    pos = 0
    for m in ep["messages"]:
        if m.get("role") == "assistant" and m.get("content") and len(m["content"].strip()) > 20:
            f = lang_feats([m["content"]])
            d = dist(f, DONOR_8B) if f else None
            out[pos] = d
            pos += 1
    return out

# Minimal tool (single read-only)
MINIMAL_TOOL = [Tool("get_policy", "Get the current store policy text.",
                     {"type": "object", "properties": {}, "required": []},
                     lambda db: {"policy": "30-day returns, refund to original payment method."})]

def run_ep(tools, seed, turns, i, cond):
    env = Env({"files": {}, "runs": 0}, tools) if tools is not None else Env({"files": {}, "runs": 0}, [])
    tool_list = list(env.tools.values()) if tools else []
    sc = {"id": "as", "condition": {"exp": "AS", "cond": cond},
          "system_prompt": tasks_cs.SYSTEM, "tools": tool_list,
          "env": env, "user_turns": turns, "grader": None}
    ep = run_episode(c, M, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["as_by_pos"] = extract_by_pos(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream AS 启动 =====")
    try:
        os.makedirs("experiments/stream_as", exist_ok=True)
        N = 10
        wd8 = workday("Qwen/Qwen3-8B", 4)
        turns = [{"stage": f"q{j}", "text": q} for j, q in enumerate(STYLE_QS)]
        results = []

        conditions = {
            "AS1_notool_wd8": (None, wd8),
            "AS1_cstools_wd8": (tasks_cs.T, wd8),
            "AS1_booktools_wd8": (tasks_book.TB, wd8),  # irrelevant tools
            "AS2_1tool_wd8": (MINIMAL_TOOL, wd8),
            "AS1_notool_none": (None, None),  # baseline
        }

        for cond, (tools, seed) in conditions.items():
            for i in range(N):
                ep = run_ep(tools, [dict(x) for x in seed] if seed else None,
                            turns, i, cond)
                for pos, d in ep["as_by_pos"].items():
                    results.append({"cond": cond, "run": i, "pos": pos, "d": d})

        with open("experiments/stream_as/tool_anchor.jsonl", "w") as f:
            for r in results: f.write(json.dumps(r) + "\n")

        from collections import defaultdict
        agg = defaultdict(list)
        for r in results:
            if r["d"] is not None:
                agg[(r["cond"], r["pos"])].append(r["d"])

        lines = ["## AS流 判决(工具定义作为风格锚定)"]
        conds = sorted(set(r["cond"] for r in results))
        max_pos = min(4, max(r["pos"] for r in results))
        lines.append(f"{'pos':3s} | " + " | ".join(f"{c.replace('AS1_','').replace('AS2_',''):14s}" for c in conds))
        for pos in range(max_pos):
            row = f"{pos:3d} | "
            for cond in conds:
                ds = agg.get((cond, pos), [])
                row += f"{sum(ds)/len(ds):14.3f}" if ds else f"{'—':>14s}"
            lines.append(row)

        # Summary: average across all positions
        lines.append("\n均值(全部位置):")
        for cond in conds:
            all_ds = [d for (c, p), ds in agg.items() if c == cond for d in ds]
            if all_ds:
                lines.append(f"- {cond:22s} = {sum(all_ds)/len(all_ds):.3f}")
        log("\n".join(lines))
    except Exception:
        log(f"AS FAILED:\n{traceback.format_exc()}")
    log("===== Stream AS 完成 =====")
