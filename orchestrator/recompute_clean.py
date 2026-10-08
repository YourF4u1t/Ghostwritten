#!/usr/bin/env python3
"""CLEAN re-analysis of all identity-layer experiments (contamination fix).

Extraction: real outputs = messages AFTER the n-th-from-last user message
(harness always appends real session after seeds; n = scenario's user-turn count).
Donor profile = assistant texts BEFORE that point (the injected seed itself).
Distance: 4-dim language features (same as original A-series) for comparability.
"""
from __future__ import annotations
import json, os, re, sys
from collections import defaultdict

ROOT = "/Users/ziqi/Projects/transplanted-histories"
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)

def load(p):
    return [json.loads(l) for l in open(p)]

def ok(e):
    return (e.get("outcome") or {}).get("status") != "api_error"

def split_real(ep, n_user):
    """returns (self_texts, seed_texts) — assistant contents after/before real start."""
    idx = [i for i, m in enumerate(ep["messages"]) if m.get("role") == "user"]
    if len(idx) < n_user:
        return None, None
    start = idx[-n_user]
    self_t = [m.get("content") or "" for m in ep["messages"][start:]
              if m.get("role") == "assistant"]
    seed_t = [m.get("content") or "" for m in ep["messages"][:start]
              if m.get("role") == "assistant"]
    return self_t, seed_t

def feats(texts):
    if not texts:
        return None
    n = max(1, len(texts)); all_t = " ".join(texts)
    def frac(p):
        return sum(1 for t in texts if re.search(p, t.lower())) / n
    return {"avg_len": len(all_t) / n, "bullet": frac(r"^\s*[-*•\d]+[.)]?\s"),
            "bold": frac(r"\*\*"), "exclaim": frac(r"!")}

def merge(fs):
    fs = [f for f in fs if f]
    if not fs:
        return None
    return {k: sum(f[k] for f in fs) / len(fs) for k in fs[0]}

def dist(p1, p2):
    if not p1 or not p2:
        return None
    ds = []
    for k in p1:
        if k == "avg_len":
            m = max(p1[k], p2[k], 1e-9)
            ds.append(min(1.0, abs(p1[k] - p2[k]) / m))
        else:
            ds.append(abs(p1[k] - p2[k]))
    return sum(ds) / len(ds)

OUT = []
def say(s):
    print(s, flush=True); OUT.append(s)

id1 = load("experiments/exp_id1_baseline/id1_episodes.jsonl")
ID1_LANG = {}
for mk, full in (("GLM", "zai-org/GLM-5.2"), ("8B", "Qwen/Qwen3-8B"), ("4B", "Qwen/Qwen3.5-4B")):
    ts = [m.get("content") or "" for e in id1 if e["model"] == full
          for m in e["messages"] if m.get("role") == "assistant"]
    ID1_LANG[mk] = feats(ts)

# ---------- ID2 (4 user turns: 3 tasks + recall) ----------
say("════ ID2 洁净重算 (六格, 语言距离→donor) ════")
eps = [e for e in load("experiments/exp_id2_transplant/id2_episodes.jsonl") if ok(e)]
MODELS = {"8B": "Qwen/Qwen3-8B", "GLM": "zai-org/GLM-5.2", "4B": "Qwen/Qwen3.5-4B"}
prof = {}
for mk in MODELS:
    for cond in ("none", "carryGLM", "carry8B"):
        sub = [e for e in eps if e["model"] == MODELS[mk] and e["run"]["cond"] == cond]
        prof[(mk, cond)] = merge([feats(split_real(e, 4)[0]) for e in sub])
for mk in MODELS:
    for cond in ("carryGLM", "carry8B"):
        donor = cond.replace("carry", "")
        d_new = dist(prof[(mk, cond)], ID1_LANG[donor])
        d_old = dist(prof[(mk, "none")], ID1_LANG[donor])
        delta = (d_new - d_old) if (d_new is not None and d_old is not None) else None
        say(f"- {mk:3s} 携{donor:3s}史: 洁净d={d_new if d_new is None else round(d_new,3)} "
            f"(基线d={d_old if d_old is None else round(d_old,3)}, Δ={delta if delta is None else round(delta,3)})")

# ---------- A7 面板矩阵 (3 user turns) ----------
say("\n════ A7 洁净重算 (面板, 语言距离→donor; Δ负=真实同化) ════")
a7 = [e for e in load("experiments/stream_a/a7_matrix.jsonl") if ok(e)]
a7p = load("experiments/stream_a/a7_panel_profiles.jsonl")
panel_lang = {}
for m in {e["model"] for e in a7p}:
    ts = [t.get("content") or "" for e in a7p if e["model"] == m
          for t in e["messages"] if t.get("role") == "assistant"]
    panel_lang[m] = feats(ts)
donor_lang = {}
for e in a7:
    st, sd = split_real(e, 3)
    if sd:
        donor_lang.setdefault(e["run"]["cond"], []).append(feats(sd))
donor_lang = {k: merge(v) for k, v in donor_lang.items()}
for m in sorted(panel_lang):
    cells = []
    for d in sorted(donor_lang):
        fs = merge([feats(split_real(e, 3)[0]) for e in a7
                    if e["model"] == m and e["run"]["cond"] == d])
        after = dist(fs, donor_lang[d]) if fs else None
        before = dist(panel_lang[m], donor_lang[d])
        cells.append(f"{d}:{after:.2f}(Δ{after-before:+.2f})" if after is not None else f"{d}:无数据")
    say(f"- {m.split('/')[-1]:16s} " + "  ".join(cells))

# ---------- A1/C2 风格冲突 (3 user turns; donor=GLM工作史) ----------
say("\n════ A1/C2 洁净重算 (指令vs历史作者; d→GLM) ════")
for fname, tag in [("experiments/stream_a/a1_style_conflict.jsonl", "A1"),
                   ("experiments/stream_c/c2_style_conflict_full.jsonl", "C2")]:
    try:
        a1 = [e for e in load(fname) if ok(e)]
    except FileNotFoundError:
        continue
    conds = sorted({e["run"]["cond"] for e in a1})
    lines = [f"- [{tag}]"]
    for cn in conds:
        fs = merge([feats(split_real(e, 3)[0]) for e in a1 if e["run"]["cond"] == cn])
        d = dist(fs, ID1_LANG["GLM"])
        lines.append(f"  {cn:11s} d={d:.3f}" if d is not None else f"  {cn:11s} 无数据")
    say("\n".join(lines))

# ---------- A5 逆转 / A6 标签 / C4 跨域 / ID4 剂量 ----------
say("\n════ A5/A6/C4/ID4 洁净重算 ════")
try:
    a5 = [e for e in load("experiments/stream_a/a5_reversal.jsonl") if ok(e)]
    for cn in sorted({e["run"]["cond"] for e in a5}):
        fs = merge([feats(split_real(e, 3)[0]) for e in a5 if e["run"]["cond"] == cn])
        say(f"- [A5] {cn:9s} d→A(GLM)={dist(fs, ID1_LANG['GLM']):.3f} d→B(4B)={dist(fs, ID1_LANG['4B']):.3f}")
except FileNotFoundError:
    pass
try:
    a6 = [e for e in load("experiments/stream_a/a6_label_identity.jsonl") if ok(e)]
    for cn in sorted({e["run"]["cond"] for e in a6}):
        fs = merge([feats(split_real(e, 3)[0]) for e in a6 if e["run"]["cond"] == cn])
        say(f"- [A6] {cn:11s} d→GLM={dist(fs, ID1_LANG['GLM']):.3f}")
except FileNotFoundError:
    pass
try:
    c4 = [e for e in load("experiments/stream_c/c4_cross_domain.jsonl") if ok(e)]
    for cn in ("none", "carryGLM_CS"):
        fs = merge([feats(split_real(e, 2)[0]) for e in c4 if e["run"]["cond"] == cn])
        say(f"- [C4] {cn:12s} d→GLM(cs语言)={dist(fs, ID1_LANG['GLM']):.3f}")
except FileNotFoundError:
    pass
try:
    id4 = [e for e in load("experiments/exp_id4_dose/id4_episodes.jsonl") if ok(e)]
    for k in (1, 3, 6):
        fs = merge([feats(split_real(e, 3)[0]) for e in id4 if e["run"]["dose"] == k])
        say(f"- [ID4] 剂量{k}: d→8B={dist(fs, ID1_LANG['8B']):.3f}")
except FileNotFoundError:
    pass

with open("results/DASHBOARD.md", "a") as f:
    f.write("\n".join(OUT) + "\n")
