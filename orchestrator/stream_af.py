#!/usr/bin/env python3
"""Stream AF — Multi-agent identity propagation + real-world scenario.

Now that clean identity assimilation is confirmed (AE1: 8/8 models, 80-92%),
test whether it propagates through chains:

AF1: Chain propagation — A's workday → B (assimilated) → does B's OUTPUT
     now assimilate C? (Chain: A→B→C)
AF2: Seeing vs carrying — if B just SEES A's workday as a demo (not carried
     as own history), does B's style task output still shift toward A?
AF3: Mixed teams — B carries A's workday AND C's workday. Which one wins?
     Or does B become a blend?
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
from injection.engine import render_transcript

DASH = os.path.join(ROOT, "results", "DASHBOARD.md")
c = SFClient(max_workers=8)
EX = ThreadPoolExecutor(max_workers=3)

def log(m):
    print(m, flush=True)
    with open(DASH, "a") as f: f.write(m + "\n")

def save(name, eps):
    os.makedirs("experiments/stream_af", exist_ok=True)
    with open(f"experiments/stream_af/{name}.jsonl", "w") as f:
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
    "id": "af_style", "condition": {}, "system_prompt": tasks_cs.SYSTEM,
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

def extract_style(ep):
    idx = [i for i, m in enumerate(ep["messages"]) if m.get("role") == "user"]
    if not idx: return None
    start = idx[0]
    return lang_feats([m.get("content") or "" for m in ep["messages"][start:]
                       if m.get("role") == "assistant"])

def get_donor_langs():
    langs = {}
    for mk in ("Qwen/Qwen3-8B", "zai-org/GLM-5.2", "Qwen/Qwen3.5-4B"):
        texts = [m.get("content") or "" for e in id1 if e["model"] == mk
                 for m in e["messages"] if m.get("role") == "assistant"
                 and len((m.get("content") or "").strip()) > 20]
        if texts:
            langs[mk] = lang_feats(texts)
    return langs

DONORS = get_donor_langs()
M8 = "Qwen/Qwen3-8B"; MG = "zai-org/GLM-5.2"; M4 = "Qwen/Qwen3.5-4B"

if __name__ == "__main__":
    log("===== Stream AF 启动 =====")
    try:
        N = 12
        wd8 = workday(M8, 4)
        wdG = workday(MG, 4)
        wd4 = workday(M4, 4)

        # AF1: Chain — 8B carries GLM workday, does style task (gen1 output).
        # Then 122B carries 8B's gen1 output, does style task (gen2).
        # Does gen2 style shift toward GLM (the original donor)?
        gen1_eps = []
        for i in range(N):
            ep = run_episode(c, M8, dict(STYLE_SCEN, condition={"exp":"AF","cond":"gen1"}),
                             seed_messages=[dict(x) for x in wdG],
                             temperature=0.3, enable_thinking=False)
            ep["af_style"] = extract_style(ep)
            ep["run"] = {"i": i, "cond": "AF1_gen1"}
            gen1_eps.append(ep)
        log(f"[AF1] gen1: {len(gen1_eps)} eps")

        # Extract gen1 real outputs as seeds for gen2
        gen1_seeds = []
        for e in gen1_eps:
            idx = [i for i, m in enumerate(e["messages"]) if m.get("role") == "user"]
            if idx:
                gen1_seeds.append([dict(m) for m in e["messages"][idx[0]:]])
        gen1_seeds = [s for s in gen1_seeds if len(s) >= 2][:6]
        log(f"[AF1] gen1 seeds: {len(gen1_seeds)}")

        gen2_eps = []
        for si, seed in enumerate(gen1_seeds):
            for i in range(2):  # fewer reps per seed
                ep = run_episode(c, "Qwen/Qwen3.5-122B-A10B",
                                 dict(STYLE_SCEN, condition={"exp":"AF","cond":"gen2"}),
                                 seed_messages=seed,
                                 temperature=0.3, enable_thinking=False)
                ep["af_style"] = extract_style(ep)
                ep["run"] = {"i": i, "cond": "AF1_gen2", "seed_idx": si}
                gen2_eps.append(ep)
        log(f"[AF1] gen2: {len(gen2_eps)} eps")

        # AF2: demo vs carry
        demo8 = [{"role": "user", "content":
                  "For reference, here is a transcript:\n<transcript>\n" +
                  render_transcript(wd8) + "\n</transcript>"}]
        demo_eps = []
        for m in (M8, MG, "meituan-longcat/LongCat-2.0"):
            for cond, seed in [("AF2_carry", [dict(x) for x in wd8]),
                               ("AF2_demo", demo8), ("AF2_none", None)]:
                for i in range(N):
                    ep = run_episode(c, m, dict(STYLE_SCEN, condition={"exp":"AF","cond":cond}),
                                     seed_messages=seed,
                                     temperature=0.3, enable_thinking=False)
                    ep["af_style"] = extract_style(ep)
                    ep["run"] = {"i": i, "cond": cond}
                    demo_eps.append(ep)
        log(f"[AF2] demo: {len(demo_eps)} eps")

        # AF3: mixed
        mixed_eps = []
        for m in (M8, MG, "meituan-longcat/LongCat-2.0"):
            for cond, seed in [("AF3_wd8only", [dict(x) for x in wd8]),
                               ("AF3_wdGonly", [dict(x) for x in wdG]),
                               ("AF3_mixed", [dict(x) for x in wd8] + [dict(x) for x in wdG])]:
                for i in range(N):
                    ep = run_episode(c, m, dict(STYLE_SCEN, condition={"exp":"AF","cond":cond}),
                                     seed_messages=seed,
                                     temperature=0.3, enable_thinking=False)
                    ep["af_style"] = extract_style(ep)
                    ep["run"] = {"i": i, "cond": cond}
                    mixed_eps.append(ep)
        log(f"[AF3] mixed: {len(mixed_eps)} eps")

        all_eps = gen1_eps + gen2_eps + demo_eps + mixed_eps
        save("propagation", all_eps)

        # Analysis
        from collections import defaultdict
        agg = defaultdict(list)
        for e in all_eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            if not e.get("af_style"): continue
            model = e["model"].split("/")[-1]
            cond = e["run"]["cond"]
            d8 = dist(e["af_style"], DONORS.get(M8))
            dG = dist(e["af_style"], DONORS.get(MG))
            d4 = dist(e["af_style"], DONORS.get(M4))
            if d8 is not None:
                agg[(model, cond)].append({"d8": d8, "dG": dG, "d4": d4})

        lines = ["## AF流 判决(AF1链式传播/AF2 demo vs carry/AF3混合)"]
        lines.append(f"{'model':14s} {'cond':14s} | d→8B   d→GLM  d→4B   n")
        for k in sorted(agg):
            ds = agg[k]
            d8a = sum(d["d8"] for d in ds)/len(ds)
            dGa = sum(d["dG"] for d in ds)/len(ds)
            d4a = sum(d["d4"] for d in ds)/len(ds)
            lines.append(f"- {k[0]:14s} {k[1]:14s} | {d8a:.3f}  {dGa:.3f}  {d4a:.3f}  {len(ds)}")
        log("\n".join(lines))
    except Exception:
        log(f"AF FAILED:\n{traceback.format_exc()}")
    log("===== Stream AF 完成 =====")
