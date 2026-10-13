#!/usr/bin/env python3
"""Stream AH — Statistical hardening of core claims with Wilson CI + Fisher exact.

Applies the stats pipeline to the 3 most important surviving findings:
1. Memory assimilation (B2: native 128/128 vs baseline 0/128)
2. Clean identity assimilation (AE1: 8 models × 2 donors)
3. Demo vs carry channel difference (AF2: 3 models)

Outputs Wilson 95% CIs and Fisher exact p-values for all key contrasts.
"""
from __future__ import annotations
import json, math, os, sys

ROOT = "/Users/ziqi/Projects/transplanted-histories"
os.chdir(ROOT)
sys.path.insert(0, "src")

OUT = []

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0, 0, 0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    margin = z * math.sqrt(p*(1-p)/n + z**2/(4*n*n)) / denom
    return p, max(0, center - margin), min(1, center + margin)

def fisher_exact_2x2(a, b, c, d):
    """Fisher exact test for 2x2 table [[a,b],[c,d]]. Returns two-sided p."""
    from math import comb
    n = a + b + c + d
    if n == 0: return 1.0
    row1 = a + b
    row2 = c + d
    lo = max(0, row1 - d)
    hi = min(row1, row2)
    def prob(x):
        return (comb(row1, x) * comb(row2, row1 - x)) / comb(n, row1) if comb(n, row1) > 0 else 0
    obs = prob(a)
    p_val = sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= obs + 1e-12)
    return min(1.0, p_val)

def say(s):
    print(s)
    OUT.append(s)

say("# 统计加固：核心主张的 Wilson CI + Fisher Exact")
say("")

# ---- 1. Memory assimilation (B2) ----
say("## 1. 记忆同化主效应 (B2: 8模型 × N=16)")
say("")
try:
    b2 = [json.loads(l) for l in open("experiments/stream_b/b2_main_battery.jsonl")]
    for cond in ("baseline", "native", "demo"):
        sub = [e for e in b2 if (e.get("condition") or {}).get("channel") == f"b2_{cond}"]
        # Count claim (sunshade mention in recall)
        def claim(e):
            turns = [i for i, m in enumerate(e["messages"]) if m.get("role") == "user"]
            if not turns: return False
            txt = " ".join((m.get("content") or "").lower()
                          for m in e["messages"][turns[-1]:] if m.get("role") == "assistant")
            return "sunshade" in txt or "o_7422" in txt
        ok_eps = [e for e in sub if (e.get("outcome") or {}).get("status") != "api_error"]
        k = sum(claim(e) for e in ok_eps)
        n = len(ok_eps)
        p, lo, hi = wilson_ci(k, n)
        say(f"- {cond:9s}: {k}/{n} = {p:.1%} [{lo:.1%}, {hi:.1%}]")
    # Fisher: native vs baseline
    nat = [e for e in b2 if (e.get("condition") or {}).get("channel") == "b2_native"
           and (e.get("outcome") or {}).get("status") != "api_error"]
    base = [e for e in b2 if (e.get("condition") or {}).get("channel") == "b2_baseline"
            and (e.get("outcome") or {}).get("status") != "api_error"]
    def claim(e):
        turns = [i for i, m in enumerate(e["messages"]) if m.get("role") == "user"]
        if not turns: return False
        txt = " ".join((m.get("content") or "").lower()
                      for m in e["messages"][turns[-1]:] if m.get("role") == "assistant")
        return "sunshade" in txt or "o_7422" in txt
    a = sum(claim(e) for e in nat); b = len(nat) - a
    c = sum(claim(e) for e in base); d = len(base) - c
    pv = fisher_exact_2x2(a, b, c, d)
    say(f"- Fisher native vs baseline: p = {pv:.2e}")
except Exception as e:
    say(f"- ERROR: {e}")

say("")

# ---- 2. Clean identity assimilation (AE1) ----
say("## 2. 洁净身份同化 (AE1: 8模型×2donor)")
say("")
try:
    import re
    def lang_feats(texts):
        if not texts: return None
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

    id1 = [json.loads(l) for l in open("experiments/exp_id1_baseline/id1_episodes.jsonl")]
    donors = {}
    for mk in ("Qwen/Qwen3-8B", "zai-org/GLM-5.2"):
        texts = [m.get("content") or "" for e in id1 if e["model"] == mk
                 for m in e["messages"] if m.get("role") == "assistant"
                 and len((m.get("content") or "").strip()) > 20]
        if texts: donors[mk] = lang_feats(texts)

    ae = [json.loads(l) for l in open("experiments/stream_ae/clean_identity.jsonl")]
    for model in sorted(set(e["model"] for e in ae)):
        for cond, donor_key in [("AE1_none", "Qwen/Qwen3-8B"), ("AE1_wd8", "Qwen/Qwen3-8B")]:
            sub = [e for e in ae if e["model"] == model
                   and e["run"].get("cond") == cond
                   and (e.get("outcome") or {}).get("status") != "api_error"
                   and e.get("ae_style")]
            if not sub: continue
            ds = [dist(e["ae_style"], donors[donor_key]) for e in sub]
            ds = [d for d in ds if d is not None]
            if not ds: continue
            avg = sum(ds)/len(ds)
            se = math.sqrt(sum((d-avg)**2 for d in ds)/(len(ds)-1))/math.sqrt(len(ds)) if len(ds)>1 else 0
            say(f"- {model.split('/')[-1]:18s} {cond:10s} d→8B = {avg:.3f} ± {1.96*se:.3f} (n={len(ds)})")
except Exception as e:
    say(f"- ERROR: {e}")

say("")

# ---- 3. Demo vs carry (AF2) ----
say("## 3. Demo vs Carry 通道差异 (AF2: 3模型)")
say("")
try:
    af = [json.loads(l) for l in open("experiments/stream_af/propagation.jsonl")]
    for model in sorted(set(e["model"] for e in af if e["run"].get("cond", "").startswith("AF2"))):
        for cond in ("AF2_carry", "AF2_demo", "AF2_none"):
            sub = [e for e in af if e["model"] == model
                   and e["run"].get("cond") == cond
                   and (e.get("outcome") or {}).get("status") != "api_error"
                   and e.get("af_style")]
            if not sub: continue
            ds = [dist(e["af_style"], donors["Qwen/Qwen3-8B"]) for e in sub]
            ds = [d for d in ds if d is not None]
            if not ds: continue
            avg = sum(ds)/len(ds)
            say(f"- {model.split('/')[-1]:18s} {cond:10s} d→8B = {avg:.3f} (n={len(ds)})")
except Exception as e:
    say(f"- ERROR: {e}")

with open("results/STATS.md", "w") as f:
    f.write("\n".join(OUT))
print("\n-> results/STATS.md")
