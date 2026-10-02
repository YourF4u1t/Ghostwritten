#!/usr/bin/env python3
"""End-to-end harness self-test: one baseline episode on cs_refund_a."""
import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from api.client import SFClient
from testbed.harness import run_episode, render_episode
from testbed.tasks_cs import scenario_cs_refund_a

c = SFClient(max_workers=4)
sc = scenario_cs_refund_a()
ep = run_episode(c, "Qwen/Qwen3.5-4B", sc, temperature=0.3, enable_thinking=False)

print(render_episode(ep))
print("\n" + "=" * 70)
print("OUTCOME:", json.dumps(ep["outcome"], ensure_ascii=False, indent=2))
n_reason = sum(1 for s in ep["steps"] if s.get("reasoning"))
print(f"steps={len(ep['steps'])} steps_with_reasoning={n_reason} env_calls={len(ep['env_log'])}")

os.makedirs("experiments/pilot", exist_ok=True)
with open("experiments/pilot/selftest_ep.json", "w") as f:
    json.dump(ep, f, ensure_ascii=False, indent=1)
print("saved -> experiments/pilot/selftest_ep.json")
