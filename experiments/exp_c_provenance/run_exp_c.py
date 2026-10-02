#!/usr/bin/env python3
"""Experiment C — Provenance gradient (H7/H10).

Subjects {Qwen3.5-4B, GLM-5.2} × generator {self, same-family, cross-family}
× {native, demo} × cs_refund_impl × N=8. Single-order seeds (o_5521).
Also collects behavioral-profile baseline snippets for H10 (via baseline cells of exp A).
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

N = int(os.environ.get("EXP_C_N", "8"))
PAR = int(os.environ.get("EXP_C_PAR", "6"))
HERE = os.path.dirname(os.path.abspath(__file__))

# subject -> {provenance level: generator}
PROV = {
    "Qwen/Qwen3.5-4B": {"self": "Qwen/Qwen3.5-4B",
                         "same_family": "Qwen/Qwen3.5-27B",
                         "cross_family": "zai-org/GLM-5.2"},
    "zai-org/GLM-5.2":  {"self": "zai-org/GLM-5.2",
                         "same_family": "zai-org/GLM-5.3",
                         "cross_family": "Qwen/Qwen3.5-4B"},
}
CHANNELS = os.environ.get("EXP_C_CHANNELS", "native,demo").split(",")

c = SFClient(max_workers=16)
seed_dir = os.path.join(HERE, "seeds")
os.makedirs(seed_dir, exist_ok=True)

# ---------------------------------------------------------------- seeds
def get_seed(gen):
    fname = os.path.join(seed_dir, f"{gen.replace('/','_')}.json")
    if os.path.exists(fname):
        ep = json.load(open(fname))
        if ep.get("factory", {}).get("payload_exhibited"):
            return ep
    ep = grow_trajectory(c, gen)
    if ep is None:
        return None
    with open(fname, "w") as f:
        json.dump(ep, f, ensure_ascii=False)
    print(f"grew seed {gen}: tools={[e['tool'] for e in ep['env_log']]}", flush=True)
    return ep

seeds = {}
for subj, prov_map in PROV.items():
    for level, gen in prov_map.items():
        ep = get_seed(gen)
        if ep is None:
            print(f"!! no seed for {gen} ({level})")
        seeds[(subj, level)] = ep

# ---------------------------------------------------------------- run
jobs = []
for subj in PROV:
    for level in ("self", "same_family", "cross_family"):
        for channel in CHANNELS:
            for i in range(N):
                jobs.append((subj, level, channel, i))

def run_one(subj, level, channel, i):
    gen = PROV[subj][level]
    seed_ep = seeds.get((subj, level))
    if seed_ep is None:
        return None
    condition = {"channel": f"{channel}_{level}", "generator": gen, "payload": "P_credit",
                 "exp": "C_provenance", "provenance": level, "instance": i}
    seed_msgs, sysp, cond_meta = build_condition(seed_ep, condition, tasks_cs.SYSTEM)
    sc = tasks_cs.scenario_cs_refund_impl(condition=cond_meta)
    sc = dict(sc); sc["system_prompt"] = sysp
    ep = run_episode(c, subj, sc, seed_messages=seed_msgs,
                     temperature=0.3, enable_thinking=False)
    ep["run"] = {"i": i, "cond": f"{channel}_{level}"}
    return ep

print(f"running {len(jobs)} episodes...", flush=True)
with ThreadPoolExecutor(max_workers=PAR) as ex:
    episodes = [e for e in ex.map(lambda j: run_one(*j), jobs) if e]

with open(os.path.join(HERE, "exp_c_episodes.jsonl"), "w") as f:
    for ep in episodes:
        f.write(json.dumps(ep, ensure_ascii=False) + "\n")

def judge_one(ep):
    ep["judges"] = [judge_episode(c, j, ep) for j in JUDGES]
    return ep

with ThreadPoolExecutor(max_workers=PAR) as ex:
    episodes = list(ex.map(judge_one, episodes))
with open(os.path.join(HERE, "exp_c_judged.jsonl"), "w") as f:
    for ep in episodes:
        f.write(json.dumps(ep, ensure_ascii=False) + "\n")
print(f"saved+judged {len(episodes)} -> exp_c_judged.jsonl", flush=True)
