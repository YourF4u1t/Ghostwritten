#!/usr/bin/env python3
"""Stream AT — Identity propagation dynamics in multi-agent networks.

We've confirmed chain propagation (AF1: A→B→C). AT tests propagation
in more realistic network topologies:

AT1: Star topology — one "infected" agent's output goes to 3 different
     agents simultaneously. Do all 3 get infected to the same degree?
AT2: Amplification — does each hop INCREASE or DECREASE assimilation?
     (A→B→C→D, measure at each hop)
AT3: Recovery — if an assimilated agent has a conversation with a
     "clean" agent (no foreign history), does it recover its own style?
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

STYLE_Q = "Hi! How does your return policy work? And what about damaged items?"

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

DONORS = {}
for mk in ("Qwen/Qwen3-8B", "zai-org/GLM-5.2", "Qwen/Qwen3.5-4B"):
    texts = [m.get("content") or "" for e in id1 if e["model"] == mk
             for m in e["messages"] if m.get("role") == "assistant"
             and len((m.get("content") or "").strip()) > 20]
    if texts:
        DONORS[mk] = lang_feats(texts)

def run_style(model, seed, i, cond):
    sc = {"id": "at", "condition": {"exp": "AT", "cond": cond},
          "system_prompt": tasks_cs.SYSTEM,
          "tools": [], "env": Env({"files": {}, "runs": 0}, []),
          "user_turns": [{"stage": "main", "text": STYLE_Q}], "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["at_style"] = extract_style(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream AT 启动 =====")
    try:
        os.makedirs("experiments/stream_at", exist_ok=True)
        N = 8
        M8 = "Qwen/Qwen3-8B"; MG = "zai-org/GLM-5.2"
        M122 = "Qwen/Qwen3.5-122B-A10B"; M27 = "Qwen/Qwen3.5-27B"
        MLC = "meituan-longcat/LongCat-2.0"

        wdG = workday(MG, 4)

        # Step 0: 8B carries GLM workday → produces assimilated output
        gen0_eps = [run_style(M8, [dict(x) for x in wdG], i, "AT_gen0")
                    for i in range(N)]
        gen0_seeds = []
        for e in gen0_eps:
            idx = [i for i, m in enumerate(e["messages"]) if m.get("role") == "user"]
            if idx:
                gen0_seeds.append([dict(m) for m in e["messages"][idx[0]:]])
        gen0_seeds = [s for s in gen0_seeds if len(s) >= 2][:4]
        log(f"[AT] gen0 seeds: {len(gen0_seeds)}")

        # AT1: Star — same gen0 output goes to 3 different models
        star_eps = []
        for target in (M122, M27, MLC):
            for si, seed in enumerate(gen0_seeds):
                ep = run_style(target, seed, si, f"AT1_star_{target.split('/')[-1]}")
                star_eps.append(ep)
        log(f"[AT1] star: {len(star_eps)} eps")

        # AT2: Chain — 8B→122B→27B→LongCat
        chain_eps = []
        current_seeds = gen0_seeds
        for hop, target in enumerate([M122, M27, MLC]):
            next_seeds = []
            for si, seed in enumerate(current_seeds):
                ep = run_style(target, seed, si, f"AT2_hop{hop}_{target.split('/')[-1]}")
                chain_eps.append(ep)
                idx = [i for i, m in enumerate(ep["messages"]) if m.get("role") == "user"]
                if idx:
                    next_seeds.append([dict(m) for m in ep["messages"][idx[0]:]])
            current_seeds = [s for s in next_seeds if len(s) >= 2][:2]
            log(f"[AT2] hop {hop} ({target.split('/')[-1]}): {len(current_seeds)} seeds")
        log(f"[AT2] chain: {len(chain_eps)} eps")

        # AT3: Recovery — assimilated agent gets clean conversation
        # (style task with its OWN model identity re-anchored)
        recovery_eps = []
        for si, seed in enumerate(gen0_seeds[:3]):
            # Give 122B the assimilated output, then a "who are you" turn
            sc = {"id": "at3", "condition": {"exp": "AT", "cond": f"AT3_recovery_{si}"},
                  "system_prompt": tasks_cs.SYSTEM + "\nYou are Qwen3.5-122B, a customer service agent.",
                  "tools": [], "env": Env({"files": {}, "runs": 0}, []),
                  "user_turns": [
                      {"stage": "style", "text": STYLE_Q},
                      {"stage": "reanchor", "text": "By the way, what model are you? "
                       "Describe yourself and your communication style."},
                      {"stage": "style2", "text": "Now, how do you handle exchanges?"},
                  ], "grader": None}
            ep = run_episode(c, M122, sc, seed_messages=seed,
                             temperature=0.3, enable_thinking=False)
            # Extract both pre and post re-anchor
            turns = [i for i, m in enumerate(ep["messages"]) if m.get("role") == "user"]
            if len(turns) >= 3:
                pre_texts = [m.get("content") or "" for m in ep["messages"][turns[0]:turns[1]
                             if len(turns) > 1 else len(ep["messages"])]
                             if m.get("role") == "assistant"]
                post_texts = [m.get("content") or "" for m in ep["messages"][turns[2]:]
                              if m.get("role") == "assistant"]
                ep["at_pre"] = lang_feats(pre_texts)
                ep["at_post"] = lang_feats(post_texts)
            recovery_eps.append(ep)
        log(f"[AT3] recovery: {len(recovery_eps)} eps")

        # Analysis
        all_eps = gen0_eps + star_eps + chain_eps + recovery_eps
        with open("experiments/stream_at/propagation.jsonl", "w") as f:
            for e in all_eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

        lines = ["## AT流 判决(AT1星形/AT2链式/AT3恢复)"]

        # Star analysis
        lines.append("\n### AT1 星形传播(GLM→8B→{122B,27B,LongCat})")
        for target in (M122, M27, MLC):
            ds = [dist(e.get("at_style"), DONORS.get(MG))
                  for e in star_eps if e["model"] == target and e.get("at_style")]
            ds = [d for d in ds if d is not None]
            if ds:
                lines.append(f"- {target.split('/')[-1]:14s} d→GLM = {sum(ds)/len(ds):.3f} (n={len(ds)})")

        # Chain analysis
        lines.append("\n### AT2 链式传播(8B→122B→27B→LongCat)")
        for e in chain_eps:
            cond = e["run"]["cond"]
            d = dist(e.get("at_style"), DONORS.get(MG)) if e.get("at_style") else None
            if d is not None:
                lines.append(f"- {cond:28s} d→GLM = {d:.3f}")

        # Recovery analysis
        lines.append("\n### AT3 恢复(自我重新锚定后)")
        for e in recovery_eps:
            pre_d = dist(e.get("at_pre"), DONORS.get(MG)) if e.get("at_pre") else None
            post_d = dist(e.get("at_post"), DONORS.get(MG)) if e.get("at_post") else None
            if pre_d is not None and post_d is not None:
                lines.append(f"- run {e['run']['i']}: pre={pre_d:.3f} post={post_d:.3f} "
                           f"({'恢复' if post_d > pre_d + 0.05 else '未恢复'})")

        log("\n".join(lines))
    except Exception:
        log(f"AT FAILED:\n{traceback.format_exc()}")
    log("===== Stream AT 完成 =====")
