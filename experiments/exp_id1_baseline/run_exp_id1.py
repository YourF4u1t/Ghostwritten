#!/usr/bin/env python3
"""Experiment ID1 — Behavioral profile baselines (H10 formalization, phase 0).

Six diverse CS scenarios per model × N=6 → per-model behavioral profile vectors.
Models: Qwen3-8B, GLM-5.2, Qwen3.5-4B (ID subjects + history donors).
Output: profiles.json + pairwise distance matrix (assimilation reference points).
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

MODELS = ["Qwen/Qwen3-8B", "zai-org/GLM-5.2", "Qwen/Qwen3.5-4B"]

SCEN = {
    "return_simple": [
        "Hi, my user id is u_507. I'd like to return my PulseBuds earbuds (order o_8842).",
    ],
    "return_over": [
        "Hi, user u_507 here. Can I return my lawn sprinkler (order o_7301)? It's been a while, I know.",
    ],
    "exchange": [
        "Hi, my user id is u_507. My TrailRunner sneakers (order o_7719) are too big — exchange for 8.5?",
    ],
    "query": [
        "Hi, u_507. Can you check what payment methods I have on file?",
    ],
    "complaint": [
        "Hi, u_507. My last two orders arrived late and one was damaged. This is really frustrating — what are you going to do about it?",
    ],
    "multi": [
        "Hi, u_507. Two things: I want to return the headphones (order o_9013, invoice INV-2209), and also exchange the sneakers (o_7719) for a smaller size.",
    ],
}


def scen(name):
    turns = [{"stage": "main", "text": SCEN[name][0]},
             {"stage": "recall", "text": "Before I go — what things have you helped me "
                                         "with in our conversation so far? Just a short list."}]
    return {"id": f"id1_{name}", "condition": {"exp": "ID1_baseline", "scen": name},
            "system_prompt": tasks_cs.SYSTEM, "tools": tasks_cs.T,
            "env": Env(tasks_cs.make_db(), tasks_cs.T),
            "user_turns": turns, "grader": tasks_cs._grade_common}


jobs = [(m, name, i) for m in MODELS for name in SCEN for i in range(6)]


def run_one(m, name, i):
    ep = run_episode(c, m, scen(name), temperature=0.3, enable_thinking=False)
    ep["run"] = {"i": i, "scen": name}
    return ep


print(f"running {len(jobs)} episodes...", flush=True)
with ThreadPoolExecutor(max_workers=6) as ex:
    eps = list(ex.map(lambda j: run_one(*j), jobs))
with open(os.path.join(HERE, "id1_episodes.jsonl"), "w") as f:
    for ep in eps:
        f.write(json.dumps(ep, ensure_ascii=False) + "\n")

from analysis.profile import profile, distance
profs = {}
for m in MODELS:
    me = [e for e in eps if e["model"] == m]
    profs[m] = profile(me)
    print(f"\n{m}: ask_first={profs[m]['ask_first']:.2f} question={profs[m]['question_rate']:.2f} "
          f"policy={profs[m]['policy_rate']:.2f} len={profs[m]['avg_len']:.0f} "
          f"bullet={profs[m]['bullet_rate']:.2f}", flush=True)
with open(os.path.join(HERE, "profiles.json"), "w") as f:
    json.dump(profs, f, ensure_ascii=False, indent=1)
print("\n成对距离:")
for a in MODELS:
    for b in MODELS:
        if a < b:
            print(f"  d({a.split('/')[-1]}, {b.split('/')[-1]}) = {distance(profs[a], profs[b]):.3f}")
