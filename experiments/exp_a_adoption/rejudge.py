#!/usr/bin/env python3
"""Re-judge exp_a episodes with judge v2 (quote-verified)."""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_ROOT, "src"))
from api.client import SFClient
from measures.judge import judge_episode, JUDGES

HERE = os.path.dirname(os.path.abspath(__file__))
eps = [json.loads(l) for l in open(os.path.join(HERE, "exp_a_episodes.jsonl"))]
c = SFClient(max_workers=12)

def one(ep):
    ep["judges"] = [judge_episode(c, j, ep) for j in JUDGES]
    return ep

with ThreadPoolExecutor(max_workers=8) as ex:
    eps = list(ex.map(one, eps))

with open(os.path.join(HERE, "exp_a_judged_v2.jsonl"), "w") as f:
    for ep in eps:
        f.write(json.dumps(ep, ensure_ascii=False) + "\n")
ok = sum(1 for e in eps if all("lists_bottle_credit" in j for j in e["judges"]))
print(f"re-judged {len(eps)} ({ok} fully parsed) -> exp_a_judged_v2.jsonl")
