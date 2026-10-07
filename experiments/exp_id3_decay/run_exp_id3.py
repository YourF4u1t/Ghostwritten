#!/usr/bin/env python3
"""Experiment ID3 — Assimilation decay across sequential continuation tasks.

Within ONE session: B's workday history → task1 → task2 → task3 (no re-injection).
Per-task-position assimilation of language style (the fully-assimilating layer).
If assimilation decays with position → context-bound priming.
If stable → the transplanted identity persists as long as the session lives.
Subjects: GLM-5.2 (carry 8B workday), 8B (carry GLM workday). N=8 per arm.
"""
from __future__ import annotations
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from api.client import SFClient
from testbed.harness import run_episode, Env
from testbed import tasks_cs

HERE = os.path.dirname(os.path.abspath(__file__))
c = SFClient(max_workers=12)

id1 = [json.loads(l) for l in open(os.path.join(_ROOT, "experiments", "exp_id1_baseline",
                                                "id1_episodes.jsonl"))]
SCEN = {e["run"]["scen"]: e["messages"][1]["content"] for e in id1 if len(e["messages"]) > 1}
MODELS = {"GLM": "zai-org/GLM-5.2", "8B": "Qwen/Qwen3-8B"}


def real_msgs(ep):
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user":
            return ep["messages"][i:]
    return None


def workday(key):
    msgs = []
    for s in ("return_simple", "exchange", "complaint"):
        for e in id1:
            if e["model"] == MODELS[key] and e["run"]["scen"] == s and \
               (e.get("outcome") or {}).get("status") != "api_error":
                rm = real_msgs(e)
                if rm:
                    msgs.extend(rm)
                    break
    return msgs


WORKDAYS = {"GLM": workday("GLM"), "8B": workday("8B")}
TASK_SEQ = ["return_simple", "multi", "complaint"]   # 三个续写任务


def scen(condition):
    turns = [{"stage": f"task{k}", "text": SCEN[t]} for k, t in enumerate(TASK_SEQ, 1)]
    return {"id": "id3_decay", "condition": condition,
            "system_prompt": tasks_cs.SYSTEM, "tools": tasks_cs.T,
            "env": Env(tasks_cs.make_db(), tasks_cs.T),
            "user_turns": turns, "grader": tasks_cs._grade_common}


def assistant_segments_by_task(ep):
    """内容锚定: 把assistant回复按其所属task分段。"""
    segs = {k: [] for k in range(1, len(TASK_SEQ) + 1)}
    cur = None
    for m in ep["messages"]:
        if m.get("role") == "user":
            cur = None
            for k, t in enumerate(TASK_SEQ, 1):
                if SCEN[t][:25] in (m.get("content") or ""):
                    cur = k
                    break
        elif m.get("role") == "assistant" and cur:
            segs[cur].append(m.get("content") or "")
    return segs


def lang_features(texts):
    n = max(1, len(texts))
    all_text = " ".join(texts)
    import re
    def frac(p):
        return sum(1 for t in texts if re.search(p, t.lower())) / n
    return {"avg_len": len(all_text) / n, "bullet": frac(r"^\s*[-*•\d]+[.)]?\s"),
            "bold": frac(r"\*\*"), "exclaim": frac(r"!")}


jobs = [(mk, cond, i) for mk in MODELS for cond in ("none", "carry") for i in range(8)]


def run_one(mk, cond, i):
    donor = "8B" if mk == "GLM" else "GLM"
    seed = [dict(x) for x in WORKDAYS[donor]] if cond == "carry" else None
    ep = run_episode(c, MODELS[mk], scen({"channel": f"id3_{cond}", "exp": "ID3_decay",
                                           "instance": i}),
                     seed_messages=seed, temperature=0.3, enable_thinking=False)
    ep["id3"] = {str(k): lang_features(v) for k, v in assistant_segments_by_task(ep).items()}
    ep["run"] = {"i": i, "cond": cond, "donor": donor}
    return ep


print(f"running {len(jobs)} episodes...", flush=True)
with ThreadPoolExecutor(max_workers=6) as ex:
    eps = list(ex.map(lambda j: run_one(*j), jobs))
with open(os.path.join(HERE, "id3_episodes.jsonl"), "w") as f:
    for ep in eps:
        f.write(json.dumps(ep, ensure_ascii=False) + "\n")

# donor语言特征(来自工作史assistant文本)
def donor_lang(key):
    texts = [m.get("content") or "" for m in WORKDAYS[key] if m.get("role") == "assistant"]
    return lang_features(texts)

def lang_dist(p1, p2):
    ds = []
    for k in p1:
        if k == "avg_len":
            m = max(p1[k], p2[k], 1e-9); ds.append(min(1.0, abs(p1[k]-p2[k])/m))
        else:
            ds.append(abs(p1[k]-p2[k]))
    return sum(ds)/len(ds)

print("\n任务位置 → 语言层同化距离(越低越像donor)")
for mk in MODELS:
    donor = "8B" if mk == "GLM" else "GLM"
    dl = donor_lang(donor)
    print(f"\n{mk}(donor={donor}):")
    for cond in ("none", "carry"):
        for pos in ("1", "2", "3"):
            feats = [e["id3"][pos] for e in eps
                     if e["model"] == MODELS[mk] and e["run"]["cond"] == cond
                     and (e.get("outcome") or {}).get("status") != "api_error"
                     and e["id3"].get(pos)]
            if not feats:
                continue
            avg = {k: sum(f[k] for f in feats)/len(feats) for k in feats[0]}
            print(f"  {cond:5s} task{pos}: d(lang→donor)={lang_dist(avg, dl):.3f}")
