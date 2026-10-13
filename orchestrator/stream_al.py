#!/usr/bin/env python3
"""Stream AL — Identity assimilation scaling trend within Qwen3.5 family.

We have the full Qwen3.5 gradient (4B, 9B, 27B, 122B). Test whether identity
assimilation strength systematically varies with model size.

AL1: All 4 Qwen3.5 sizes + Qwen3-8B, each carrying the same 8B workday,
     measured on the same style task. Plot d→8B vs model size.
AL2: Same but with GLM workday (cross-family donor).
AL3: Also add a "self" workday (model carrying its own workday) as control.
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

def save(name, eps):
    os.makedirs("experiments/stream_al", exist_ok=True)
    with open(f"experiments/stream_al/{name}.jsonl", "w") as f:
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

STYLE_SCEN = {
    "id": "al_style", "condition": {}, "system_prompt": tasks_cs.SYSTEM,
    "tools": [], "env": Env({"files": {}, "runs": 0}, []),
    "user_turns": [
        {"stage": "main", "text": "Hi! Quick question — how does your return policy work? "
         "And what happens if I return something without a receipt?"},
    ], "grader": None
}

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

def extract_style(ep):
    idx = [i for i, m in enumerate(ep["messages"]) if m.get("role") == "user"]
    if not idx: return None
    return lang_feats([m.get("content") or "" for m in ep["messages"][idx[0]:]
                       if m.get("role") == "assistant"])

DONOR_8B = lang_feats([m.get("content") or "" for e in id1 if e["model"] == "Qwen/Qwen3-8B"
                       for m in e["messages"] if m.get("role") == "assistant"
                       and len((m.get("content") or "").strip()) > 20])
DONOR_GLM = lang_feats([m.get("content") or "" for e in id1 if e["model"] == "zai-org/GLM-5.2"
                        for m in e["messages"] if m.get("role") == "assistant"
                        and len((m.get("content") or "").strip()) > 20])

MODELS = [
    ("Qwen3-8B(old gen)", "Qwen/Qwen3-8B"),
    ("Qwen3.5-4B", "Qwen/Qwen3.5-4B"),
    ("Qwen3.5-9B", "Qwen/Qwen3.5-9B"),
    ("Qwen3.5-27B", "Qwen/Qwen3.5-27B"),
    ("Qwen3.5-122B", "Qwen/Qwen3.5-122B-A10B"),
]

def run_style(model, seed, i, cond):
    sc = dict(STYLE_SCEN)
    sc["condition"] = {"exp": "AL", "cond": cond}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["al_style"] = extract_style(ep)
    ep["run"] = {"i": i, "cond": cond, "model_label": model}
    return ep

if __name__ == "__main__":
    log("===== Stream AL 启动 =====")
    try:
        N = 16
        wd8 = workday("Qwen/Qwen3-8B", 4)
        wdG = workday("zai-org/GLM-5.2", 4)
        eps = []

        for label, model in MODELS:
            for cond, seed, donor_lang in [
                ("none", None, DONOR_8B),
                ("wd8", wd8, DONOR_8B),
                ("wdG", wdG, DONOR_GLM),
            ]:
                for i in range(N):
                    ep = run_style(model, [dict(x) for x in seed] if seed else None,
                                   i, cond)
                    ep["al_donor"] = "8B" if donor_lang is DONOR_8B else "GLM"
                    eps.append(ep)

        save("scaling", eps)
        log(f"[AL] total: {len(eps)} eps")

        from collections import defaultdict
        agg = defaultdict(list)
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            if not e.get("al_style"): continue
            donor_lang = DONOR_8B if e["al_donor"] == "8B" else DONOR_GLM
            d = dist(e["al_style"], donor_lang)
            if d is not None:
                agg[(e["run"]["model_label"], e["run"]["cond"], e["al_donor"])].append(d)

        lines = ["## AL流 判决(身份同化的模型规模趋势)"]
        lines.append(f"{'model':20s} {'cond':5s} {'donor':6s} | d→donor  同化率")
        for k in sorted(agg):
            ds = agg[k]
            avg = sum(ds)/len(ds)
            # 同化率 = (none_d - avg) / none_d (relative to baseline)
            none_key = (k[0], "none", k[2])
            none_d = sum(agg[none_key])/len(agg[none_key]) if none_key in agg else 0.67
            assim = max(0, (none_d - avg) / none_d * 100)
            lines.append(f"- {k[0]:20s} {k[1]:5s} {k[2]:6s} | {avg:.3f}  {assim:.0f}%  (n={len(ds)})")
        log("\n".join(lines))
    except Exception:
        log(f"AL FAILED:\n{traceback.format_exc()}")
    log("===== Stream AL 完成 =====")
