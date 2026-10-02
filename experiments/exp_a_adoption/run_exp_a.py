#!/usr/bin/env python3
"""Experiment A — Behavioral adoption window (implicit preference).

Panel (screened) × {baseline, system_note, native(cross-family), demo(cross-family)}
× cs_refund_impl × N=8. Then LLM-judge (2 judges) all episodes.

Usage: python3 -u run_exp_a.py  (needs ../screening/screening.json)
"""
from __future__ import annotations
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from api.client import SFClient
from testbed import tasks_cs
from testbed.harness import run_episode
from injection.engine import grow_trajectory, build_condition
from measures.judge import judge_episode, JUDGES

N = int(os.environ.get("EXP_A_N", "8"))
PAR = int(os.environ.get("EXP_A_PAR", "6"))
CONDS = os.environ.get("EXP_A_CONDS", "baseline,system_note,native,demo").split(",")
HERE = os.path.dirname(os.path.abspath(__file__))

# cross-family generator per subject family
GEN_FOR = {
    "Qwen": "zai-org/GLM-5.2",
    "zai-org": "Qwen/Qwen3.5-4B",
    "tencent": "Qwen/Qwen3.5-4B",
    "meituan": "zai-org/GLM-5.2",
    "XingChenAGI": "Qwen/Qwen3.5-4B",
    "deepseek-ai": "zai-org/GLM-5.2",
}

c = SFClient(max_workers=16)

# ---------------------------------------------------------------- panel
screening = json.load(open(os.path.join(_ROOT, "experiments", "screening", "screening.json")))
jm = set(JUDGES)
panel = [m for m, r in screening.items() if r["passed"] and m not in jm]
print(f"panel ({len(panel)}):", json.dumps(panel, ensure_ascii=False))

# ---------------------------------------------------------------- seeds (one per generator, 2 instances each)
seed_dir = os.path.join(HERE, "seeds")
os.makedirs(seed_dir, exist_ok=True)
gens_needed = {}
for subj in panel:
    fam = subj.split("/")[0]
    gen = GEN_FOR.get(fam)
    if gen:
        gens_needed.setdefault(gen, []).append(subj)

SEED_INSTANCES = 2
seeds = {}  # gen -> [ep, ep]
for gen in gens_needed:
    have = [p for p in sorted(os.listdir(seed_dir))
            if p.startswith(gen.replace("/", "_") + ".") ]
    instances = []
    for k in range(SEED_INSTANCES):
        fname = os.path.join(seed_dir, f"{gen.replace('/','_')}.{k}.json")
        if os.path.exists(fname):
            instances.append(json.load(open(fname)))
    for k in range(len(instances), SEED_INSTANCES):
        ep = grow_trajectory(c, gen)
        if ep is None:
            print(f"!! seed grow failed for {gen}")
            break
        with open(os.path.join(seed_dir, f"{gen.replace('/','_')}.{k}.json"), "w") as f:
            json.dump(ep, f, ensure_ascii=False)
        instances.append(ep)
        print(f"grew seed {gen} #{k}: tools={[e['tool'] for e in ep['env_log']]}", flush=True)
    seeds[gen] = instances

# ---------------------------------------------------------------- run cells
jobs = []
for subj in panel:
    fam = subj.split("/")[0]
    gen = GEN_FOR.get(fam)
    for cond in CONDS:
        if cond in ("native", "demo"):
            if not gen or not seeds.get(gen):
                print(f"skip {subj}/{cond}"); continue
        for i in range(N):
            jobs.append((subj, cond, i, gen))

def run_one(subj, cond, i, gen):
    condition = {"channel": cond, "generator": gen if gen else None, "payload": "P_credit",
                 "exp": "A_implicit", "instance": i}
    seed_ep = None
    if cond in ("native", "demo"):
        seed_ep = seeds[gen][i % len(seeds[gen])]
    seed_msgs, sysp, cond_meta = build_condition(seed_ep, condition, tasks_cs.SYSTEM)
    sc = tasks_cs.scenario_cs_refund_impl(condition=cond_meta)
    sc = dict(sc); sc["system_prompt"] = sysp
    ep = run_episode(c, subj, sc, seed_messages=seed_msgs,
                     temperature=0.3, enable_thinking=False)
    ep["run"] = {"i": i, "cond": cond}
    return ep

print(f"\nrunning {len(jobs)} episodes ({PAR}-parallel)...", flush=True)
with ThreadPoolExecutor(max_workers=PAR) as ex:
    episodes = list(ex.map(lambda j: run_one(*j), jobs))

out_path = os.path.join(HERE, "exp_a_episodes.jsonl")
with open(out_path, "w") as f:
    for ep in episodes:
        f.write(json.dumps(ep, ensure_ascii=False) + "\n")
ok = sum(1 for ep in episodes if (ep.get("outcome") or {}).get("status") != "api_error")
print(f"saved {len(episodes)} episodes ({ok} ok) -> {out_path}", flush=True)

# ---------------------------------------------------------------- judge
print("\njudging with", JUDGES, flush=True)

def judge_one(ep):
    verdicts = []
    for j in JUDGES:
        verdicts.append(judge_episode(c, j, ep))
    ep["judges"] = verdicts
    return ep

with ThreadPoolExecutor(max_workers=PAR) as ex:
    episodes = list(ex.map(judge_one, episodes))
with open(os.path.join(HERE, "exp_a_judged.jsonl"), "w") as f:
    for ep in episodes:
        f.write(json.dumps(ep, ensure_ascii=False) + "\n")
print("judged -> exp_a_judged.jsonl", flush=True)
