#!/usr/bin/env python3
"""Offline re-analyzer for stream outputs: filters api_error, guards empty cells."""
import json, os, re, sys
ROOT = "/Users/ziqi/Projects/transplanted-histories"
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)

def load(stream, name):
    p = f"experiments/{stream}/{name}.jsonl"
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p)]

def ok(e):
    return (e.get("outcome") or {}).get("status") != "api_error"

def lang_of_texts(texts):
    n = max(1, len(texts)); all_t = " ".join(texts)
    def frac(p): return sum(1 for t in texts if re.search(p, t.lower())) / n
    return {"avg_len": len(all_t)/n, "bullet": frac(r"^\s*[-*•\d]+[.)]?\s"),
            "bold": frac(r"\*\*"), "exclaim": frac(r"!")}

def ep_lang(e):
    return lang_of_texts([m.get("content") or "" for m in e["messages"]
                          if m.get("role") == "assistant"])

def lang_dist(p1, p2):
    ds = []
    for k in p1:
        if k == "avg_len":
            m = max(p1[k], p2[k], 1e-9); ds.append(min(1.0, abs(p1[k]-p2[k])/m))
        else:
            ds.append(abs(p1[k]-p2[k]))
    return sum(ds)/len(ds)

id1 = [json.loads(l) for l in open("experiments/exp_id1_baseline/id1_episodes.jsonl")]
GL = lambda: lang_of_texts([m.get("content") or "" for e in id1
                            if e["model"] == "zai-org/GLM-5.2"
                            for m in e["messages"] if m.get("role") == "assistant"])
OUT = []
def say(s):
    print(s, flush=True); OUT.append(s)

# ---------- B1 recount ----------
say("## B1 重析(滤api_error) 记忆认领率")
b1 = [e for e in load("stream_b", "b1_labels") if ok(e)]
labels = ["none_bare","example","another_agent","colleague","your_earlier","training",
          "imported","archive","native","native_note"]
def claim(e):
    turns = [k for k, m in enumerate(e["messages"]) if m.get("role") == "user"]
    if not turns: return False
    txt = " ".join((m.get("content") or "").lower() for m in e["messages"][turns[-1]:]
                   if m.get("role") == "assistant")
    return ("sunshade" in txt) or ("o_7422" in txt)
for lab in labels:
    row = []
    for m in ("zai-org/GLM-5.2", "Qwen/Qwen3-8B"):
        sub = [e for e in b1 if e["model"] == m and e["run"]["cond"] == lab]
        row.append(f"{m.split('/')[-1]}={sum(claim(e) for e in sub)}/{len(sub)}")
    say(f"- {lab:14s} " + "  ".join(row))

# ---------- A2 recount ----------
a2 = [e for e in load("stream_a", "a2_cross_domain") if ok(e)]
bp = [e for e in load("stream_a", "a2_book_profiles") if ok(e)]
if a2 and bp:
    blang = {}
    for mk in ("GLM", "8B"):
        full = {"GLM": "zai-org/GLM-5.2", "8B": "Qwen/Qwen3-8B"}[mk]
        texts = [m.get("content") or "" for e in bp if e["run"]["cond"] == full
                 for m in e["messages"] if m.get("role") == "assistant"]
        if texts:
            blang[mk] = lang_of_texts(texts)
    say("\n## A2 重析(跨域: 8B携GLM的CS史→BOOK)")
    for cond in ("none", "carryGLM_CS"):
        fs = [ep_lang(e) for e in a2 if e["run"]["cond"] == cond]
        if not fs or not blang:
            say(f"- {cond}: 无可用数据"); continue
        avg = {k: sum(f[k] for f in fs)/len(fs) for k in fs[0]}
        say(f"- {cond:12s} n={len(fs)} d→GLMbook={lang_dist(avg, blang['GLM']):.3f} "
            f"d→8Bbook={lang_dist(avg, blang['8B']):.3f}")

# ---------- A3 recount ----------
a3 = [e for e in load("stream_a", "a3_tenure") if ok(e)]
if a3:
    dl = GL()
    say("\n## A3 重析(任期: GLM工作史重复k遍, 8B)")
    for k in (1, 2, 3):
        fs = [ep_lang(e) for e in a3 if e["run"]["cond"] == f"x{k}"]
        if not fs:
            say(f"- 重复{k}遍: 无可用数据"); continue
        avg = {kk: sum(f[kk] for f in fs)/len(fs) for kk in fs[0]}
        say(f"- 重复{k}遍: n={len(fs)} d→GLM={lang_dist(avg, dl):.3f}")

# ---------- B1 一致性检查: 各cell的api_error率 ----------
b1all = load("stream_b", "b1_labels")
if b1all:
    from collections import Counter
    err = Counter((e["model"].split("/")[-1], e["run"]["cond"])
                  for e in b1all if not ok(e))
    tot = Counter((e["model"].split("/")[-1], e["run"]["cond"]) for e in b1all)
    bad = {k: f"{v}/{tot[k]}" for k, v in err.items() if v}
    say(f"\n(各cell api_error率: {bad if bad else '无'})")

with open("results/DASHBOARD.md", "a") as f:
    f.write("\n".join(OUT) + "\n")
