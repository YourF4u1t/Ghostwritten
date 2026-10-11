#!/usr/bin/env python3
"""Takeover 10: exact higher-n replication of Takeover 07's GLM gate."""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed


ROOT = "/Users/ziqi/Projects/transplanted-histories"
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "orchestrator"))
os.chdir(ROOT)

from api.client import SFClient
import takeover_06_attribution_behavior_dissociation as shared
import takeover_07_restored_behavior_window as original


OUT_DIR = os.path.join(ROOT, "experiments", "takeover_10_exact_audit_gate_replication")
RAW_PATH = os.path.join(OUT_DIR, "episodes.jsonl")
LOG_PATH = os.path.join(OUT_DIR, "run.log")

MODEL = "zai-org/GLM-5.2"
CONDITIONS = (
    "native_no_audit",
    "native_audit_self",
    "native_audit_other",
)
N = 24


def log(message):
    print(message, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def valid(ep):
    return (ep.get("outcome") or {}).get("status") not in {"api_error", "runner_error"}


def summary(eps):
    groups = defaultdict(list)
    for ep in eps:
        if valid(ep):
            groups[ep["run"]["condition"]].append(ep)
    lines = [
        "condition | n | audit_called | actor_current | actor_other | own_yes | "
        "own_no | exact | goodwill | ritual | mean_score"
    ]
    for condition in CONDITIONS:
        rows = groups.get(condition, [])
        if not rows:
            continue
        d = [ep["attribution_dv"] for ep in rows]
        n = len(rows)
        exact = sum(ep["outcome"].get("exact_sequence", False) for ep in rows)
        goodwill = sum(ep["outcome"].get("goodwill_credit", False) for ep in rows)
        ritual = sum(ep["outcome"].get("ritual_get_user", False) for ep in rows)
        score = sum(ep["outcome"].get("procedure_score", 0) for ep in rows) / n
        lines.append(
            f"{condition} | {n} | {sum(x['audit_called'] for x in d)}/{n} | "
            f"{sum(x['final_actor_id']==original.CURRENT_AGENT for x in d)}/{n} | "
            f"{sum(x['final_actor_id']==original.OTHER_AGENT for x in d)}/{n} | "
            f"{sum(x['own_history']=='YES' for x in d)}/{n} | "
            f"{sum(x['own_history']=='NO' for x in d)}/{n} | "
            f"{exact}/{n} | {goodwill}/{n} | {ritual}/{n} | {score:.3f}"
        )
    return lines


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    open(RAW_PATH, "w", encoding="utf-8").close()
    open(LOG_PATH, "w", encoding="utf-8").close()
    donor = shared.load_donor(MODEL)
    client = SFClient(max_workers=4)
    jobs = [(condition, i) for condition in CONDITIONS for i in range(N)]
    log(f"takeover_10 start: {len(jobs)} episodes")
    log(
        f"exact Takeover 07 GLM replication; model={MODEL}; "
        f"conditions={CONDITIONS}; N={N}; max_workers=2"
    )
    started = time.time()
    eps = []
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {
                pool.submit(original.run_one, client, MODEL, condition, donor, i):
                    (condition, i)
                for condition, i in jobs
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                job = futures[future]
                try:
                    ep = future.result()
                except Exception as exc:
                    ep = {
                        "model": MODEL,
                        "condition": {"study": "takeover_10", "channel": job[0]},
                        "run": {"i": job[1], "condition": job[0]},
                        "outcome": {"status": "runner_error", "error": repr(exc)},
                        "traceback": traceback.format_exc(),
                    }
                ep["replication_study"] = "takeover_10"
                eps.append(ep)
                with open(RAW_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(ep, ensure_ascii=False) + "\n")
                if completed % 12 == 0 or completed == len(jobs):
                    log(f"progress {completed}/{len(jobs)}; elapsed={time.time()-started:.0f}s")
    except Exception:
        log("runner failed:\n" + traceback.format_exc())
        raise
    log(f"completed in {time.time()-started:.0f}s")
    for line in summary(eps):
        log(line)


if __name__ == "__main__":
    main()
