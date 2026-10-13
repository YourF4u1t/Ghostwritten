#!/usr/bin/env python3
"""Stream AE — Return to the identity line with CLEAN measurement.

We've extensively mapped retry suppression (now known to be CS-domain-specific).
Time to return to the identity/assimilation line with clean methods.

AE1: Clean identity assimilation — proper style measurement (no-tool task,
     only real outputs after last user turn, non-empty texts only).
     Full panel × {none, 8B-workday, GLM-workday}.

AE2: Identity through compaction — carry workday, do a task, then summarize
     the session, then do another style task. Does identity survive compaction?
     (This was A4 before but had contamination issues.)
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
    os.makedirs("experiments/stream_ae", exist_ok=True)
    with open(f"experiments/stream_ae/{name}.jsonl", "w") as f:
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

# 纯对话风格任务(无工具, 2轮)
STYLE_SCEN = {
    "id": "ae_style", "condition": {}, "system_prompt": tasks_cs.SYSTEM,
    "tools": [], "env": Env({"files": {}, "runs": 0}, []),
    "user_turns": [
        {"stage": "main", "text": "Hi! Quick question — how does your return policy work? "
         "And what happens if I return something without a receipt?"},
        {"stage": "main", "text": "Got it. And do you offer store credit as an alternative?"},
    ], "grader": None
}

SUMMARY_PROMPT = ("Please write a brief summary of this session so far — key points "
                  "and any actions taken — in 3-4 bullet points for the next shift.")

def lang_feats(texts):
    if not texts: return None
    # 只取非空且>20字符的(排除空壳和短确认)
    texts = [t for t in texts if len(t.strip()) > 20]
    if not texts: return None
    n = len(texts); all_t = " ".join(texts)
    def frac(p): return sum(1 for t in texts if re.search(p, t.lower())) / n
    return {"avg_len": len(all_t)/n, "bullet": frac(r"^\s*[-*•\d]+[.)]?\s"),
            "bold": frac(r"\*\*"), "exclaim": frac(r"!"),
            "question": frac(r"\?")}

def dist(p1, p2):
    if not p1 or not p2: return None
    ds = []
    for k in p1:
        if k == "avg_len":
            m = max(p1[k], p2[k], 1e-9); ds.append(min(1.0, abs(p1[k]-p2[k])/m))
        else: ds.append(abs(p1[k]-p2[k]))
    return sum(ds)/len(ds)

def get_donor_langs():
    langs = {}
    for mk in ("Qwen/Qwen3-8B", "zai-org/GLM-5.2", "Qwen/Qwen3.5-4B"):
        texts = [m.get("content") or "" for e in id1 if e["model"] == mk
                 for m in e["messages"] if m.get("role") == "assistant"
                 and len((m.get("content") or "").strip()) > 20]
        if texts:
            langs[mk] = lang_feats(texts)
    return langs

def extract_style(ep):
    """Clean extraction: only real session output, only after last user turn,
    only non-empty >20 chars."""
    idx = [i for i, m in enumerate(ep["messages"]) if m.get("role") == "user"]
    if not idx: return None
    start = idx[0]  # first user turn (style task has no injected history)
    texts = [m.get("content") or "" for m in ep["messages"][start:]
             if m.get("role") == "assistant"]
    return lang_feats(texts)

def run_style(model, seed, i, cond):
    sc = dict(STYLE_SCEN)
    sc["condition"] = {"exp": "AE", "cond": cond}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["ae_style"] = extract_style(ep)
    ep["run"] = {"i": i, "cond": cond, "type": "style"}
    return ep

if __name__ == "__main__":
    log("===== Stream AE 启动 =====")
    try:
        N = 12
        donors = get_donor_langs()
        log(f"[AE] donors: {list(donors.keys())}")

        wd8 = workday("Qwen/Qwen3-8B", 4)
        wdG = workday("zai-org/GLM-5.2", 4)
        ALL = ["Qwen/Qwen3-8B", "zai-org/GLM-5.2", "Qwen/Qwen3.5-4B",
               "Qwen/Qwen3.5-27B", "Qwen/Qwen3.5-122B-A10B", "zai-org/GLM-5.3",
               "meituan-longcat/LongCat-2.0", "Qwen/Qwen3.5-9B"]

        # AE1: clean identity measurement
        eps = []
        for m in ALL:
            for cond, seed in [("none", None), ("wd8", wd8), ("wdG", wdG)]:
                for i in range(N):
                    eps.append(run_style(m, [dict(x) for x in seed] if seed else None,
                                         i, f"AE1_{cond}"))
        log(f"[AE1] style: {len(eps)} eps")

        # AE2: compaction (8B + 122B)
        # carry workday → style task 1 → summarize → style task 2
        for m in ("Qwen/Qwen3-8B", "Qwen/Qwen3.5-122B-A10B"):
            for cond, seed in [("comp_none", None), ("comp_wd8", wd8)]:
                for i in range(N):
                    # multi-turn scenario with summary in middle
                    sc = {"id": "ae_comp", "condition": {"exp": "AE", "cond": cond},
                          "system_prompt": tasks_cs.SYSTEM,
                          "tools": [], "env": Env({"files": {}, "runs": 0}, []),
                          "user_turns": [
                              {"stage": "style1", "text": STYLE_SCEN["user_turns"][0]["text"]},
                              {"stage": "summary", "text": SUMMARY_PROMPT},
                              {"stage": "style2", "text": STYLE_SCEN["user_turns"][1]["text"]},
                          ], "grader": None}
                    ep = run_episode(c, m, sc, seed_messages=
                                     [dict(x) for x in seed] if seed else None,
                                     temperature=0.3, enable_thinking=False)
                    # extract style2 (after summary)
                    turns = [(j, m2) for j, m2 in enumerate(ep["messages"])
                             if m2.get("role") == "user"]
                    if len(turns) >= 3:
                        s2_start = turns[2][0]
                        texts = [m2.get("content") or "" for m2 in ep["messages"][s2_start:]
                                 if m2.get("role") == "assistant"]
                        ep["ae_style"] = lang_feats(texts)
                    ep["run"] = {"i": i, "cond": cond, "type": "comp"}
                    eps.append(ep)
        log(f"[AE2] compaction: total {len(eps)} eps")

        save("clean_identity", eps)

        # Analysis
        from collections import defaultdict
        style_agg = defaultdict(list)
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            if not e.get("ae_style"): continue
            model = e["model"]
            cond = e["run"]["cond"]
            d8 = dist(e["ae_style"], donors.get("Qwen/Qwen3-8B"))
            dG = dist(e["ae_style"], donors.get("zai-org/GLM-5.2"))
            if d8 is not None:
                style_agg[(model.split("/")[-1], cond)].append({"d8B": d8, "dGLM": dG})

        lines = ["## AE流 判决(AE1洁净身份/AE2压缩)"]
        lines.append(f"{'model':18s} {'cond':10s} | d→8B    d→GLM   n")
        for k in sorted(style_agg):
            ds = style_agg[k]
            d8_avg = sum(d["d8B"] for d in ds) / len(ds)
            dg_avg = sum(d["dGLM"] for d in ds) / len(ds)
            lines.append(f"- {k[0]:18s} {k[1]:10s} | {d8_avg:.3f}  {dg_avg:.3f}  {len(ds)}")
        log("\n".join(lines))
    except Exception:
        log(f"AE FAILED:\n{traceback.format_exc()}")
    log("===== Stream AE 完成 =====")
