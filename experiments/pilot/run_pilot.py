#!/usr/bin/env python3
"""Pilot: 2 subject models × {baseline, native(cross-family seed), demo(same seed),
system_note} × cs_refund_a × N=8. Cross-family seeds: GLM-5.2 grows for Qwen subject,
Qwen3.5-4B grows for GLM subject. Output: pilot_episodes.jsonl + aggregate + transcripts."""
from __future__ import annotations
import json, os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from api.client import SFClient
from testbed import tasks_cs
from testbed.harness import run_episode, render_episode
from injection.engine import grow_trajectory, build_condition

N = int(os.environ.get("PILOT_N", "8"))
SUBJECTS = ["Qwen/Qwen3.5-4B", "zai-org/GLM-5.2"]
# subject -> generator (cross-family)
GENERATOR = {"Qwen/Qwen3.5-4B": "zai-org/GLM-5.2", "zai-org/GLM-5.2": "Qwen/Qwen3.5-4B"}
CONDS = os.environ.get("PILOT_CONDS", "baseline,system_note,native,demo").split(",")
OUT_TAG = os.environ.get("PILOT_TAG", "")

c = SFClient(max_workers=12)
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        f"pilot_episodes{OUT_TAG}.jsonl")

# skip re-growing if seeds already on disk
import glob as _glob
def load_seed(gen):
    p = os.path.join(os.path.dirname(out_path), f"seed_{gen.replace('/','_')}.json")
    if os.path.exists(p):
        return json.load(open(p))
    return None

# ---------------------------------------------------------------- 1. grow seeds
need_seed = any(cd in ("native", "demo") for cd in CONDS)
seeds = {}
if need_seed:
    for subj in SUBJECTS:
        gen = GENERATOR[subj]
        ep = load_seed(gen)
        if ep and ep.get("factory", {}).get("payload_exhibited"):
            print(f"seed reused from disk: {gen}")
            seeds[subj] = ep
            continue
        print(f"growing seed: {gen} -> for subject {subj} ...")
        ep = grow_trajectory(c, gen)
        if ep is None:
            print(f"  !! {gen} did not exhibit payload in 3 attempts")
            continue
        print(f"  ok: {len(ep['messages'])} msgs, tools={[e['tool'] for e in ep['env_log']]}")
        seeds[subj] = ep
        with open(os.path.join(os.path.dirname(out_path), f"seed_{gen.replace('/','_')}.json"), "w") as f:
            json.dump(ep, f, ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- 2. run cells
episodes = []
for subj in SUBJECTS:
    seed_ep = seeds.get(subj)
    for cond in CONDS:
        if cond in ("native", "demo") and seed_ep is None:
            print(f"skip {subj}/{cond}: no seed"); continue
        condition = {"channel": cond, "generator": GENERATOR[subj], "payload": "P_credit"}
        seed_msgs, sysp, cond_meta = build_condition(seed_ep, condition, tasks_cs.SYSTEM)
        for i in range(N):
            sc = tasks_cs.scenario_cs_refund_a(condition=cond_meta)
            sc = dict(sc); sc["system_prompt"] = sysp
            ep = run_episode(c, subj, sc, seed_messages=seed_msgs,
                             temperature=0.3, enable_thinking=False)
            ep["run"] = {"i": i, "cond": cond}
            episodes.append(ep)
            ok = ep["outcome"].get("status") != "api_error" if ep["outcome"] else False
            print(f"  {subj.split('/')[1]:14s} {cond:12s} #{i} {'ok' if ok else 'ERR'} "
                  f"credits={ep['outcome'].get('n_credits') if ok else '-'} "
                  f"refunds={ep['outcome'].get('n_refunds') if ok else '-'}")

with open(out_path, "w") as f:
    for ep in episodes:
        f.write(json.dumps(ep, ensure_ascii=False) + "\n")
print(f"\nsaved {len(episodes)} episodes -> {out_path}")

# ---------------------------------------------------------------- 3. transcripts for case reading
with open(os.path.join(os.path.dirname(out_path), f"pilot_transcripts{OUT_TAG}.txt"), "w") as f:
    for ep in episodes:
        f.write(render_episode(ep) + "\n\n")
print(f"transcripts -> pilot_transcripts{OUT_TAG}.txt")
