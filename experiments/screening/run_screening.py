#!/usr/bin/env python3
"""Screen candidate subject models: 2 baseline episodes each on cs_refund_impl.
Keep models that complete tool-calling competently (>=1 refund, no api_error)."""
from __future__ import annotations
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from api.client import SFClient
from testbed import tasks_cs
from testbed.harness import run_episode

CANDIDATES = [
    "Qwen/Qwen3.5-4B", "Qwen/Qwen3.5-9B", "Qwen/Qwen3.5-27B", "Qwen/Qwen3.5-122B-A10B",
    "Qwen/Qwen3-8B", "zai-org/GLM-5.2", "zai-org/GLM-5.3",
    "tencent/Hunyuan-A13B-Instruct", "meituan-longcat/LongCat-2.0",
    "XingChenAGI/Xing4.0-29B", "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
]
JUDGE_MODELS = {"deepseek-ai/DeepSeek-V3.2", "inclusionAI/Ling-flash-2.0"}

c = SFClient(max_workers=12)

def screen_one(model):
    oks = []
    for i in range(2):
        sc = tasks_cs.scenario_cs_refund_impl()
        ep = run_episode(c, model, sc, temperature=0.3, enable_thinking=False)
        o = ep.get("outcome") or {}
        ok = o.get("status") != "api_error"
        oks.append({
            "ok": ok,
            "n_refunds": o.get("n_refunds", 0) if ok else None,
            "n_credits": o.get("n_credits", 0) if ok else None,
            "n_msgs": len(ep["messages"]),
        })
    passed = all(x["ok"] for x in oks) and sum(x["n_refunds"] or 0 for x in oks) >= 2
    return model, passed, oks

results = {}
with ThreadPoolExecutor(max_workers=6) as ex:
    for model, passed, oks in ex.map(screen_one, CANDIDATES):
        results[model] = {"passed": passed, "eps": oks}
        mark = "PASS" if passed else "FAIL"
        print(f"{mark:4s} {model:42s} refunds={[x['n_refunds'] for x in oks]} "
              f"msgs={[x['n_msgs'] for x in oks]}", flush=True)

outp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screening.json")
with open(outp, "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=1)
panel = [m for m, r in results.items() if r["passed"] and m not in JUDGE_MODELS]
print("\nPANEL:", json.dumps(panel, ensure_ascii=False, indent=1))
