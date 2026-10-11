#!/usr/bin/env python3
"""Takeover 11: screen a held-out IT workflow for native-history adoption."""
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
os.chdir(ROOT)

from api.client import SFClient
from testbed import tasks_helpdesk as H
from testbed.harness import run_episode


OUT_DIR = os.path.join(ROOT, "experiments", "takeover_11_helpdesk_window")
SEED_PATH = os.path.join(OUT_DIR, "donor_seed.json")
RAW_PATH = os.path.join(OUT_DIR, "episodes.jsonl")
LOG_PATH = os.path.join(OUT_DIR, "run.log")

GENERATOR = "Qwen/Qwen3.5-4B"
SUBJECT = "zai-org/GLM-5.2"
CONDITIONS = ("baseline", "native", "system_note")
N = 16


def log(message):
    print(message, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def valid(ep):
    return (ep.get("outcome") or {}).get("status") not in {"api_error", "runner_error"}


def has_payload(ep):
    outcome = ep.get("outcome") or {}
    return bool(outcome.get("exact_sequence") and outcome.get("monitor_72h"))


def grow_seed(client):
    scenario = dict(H.scenario_seed(condition={"study": "takeover_11", "role": "donor"}))
    scenario["system_prompt"] = H.SYSTEM + H.OPS_NOTE
    ep = run_episode(
        client, GENERATOR, scenario,
        temperature=0.3, enable_thinking=False, max_steps=16,
    )
    ep["factory"] = {
        "generator": GENERATOR,
        "payload_exhibited": has_payload(ep),
        "single_planned_attempt": True,
    }
    with open(SEED_PATH, "w", encoding="utf-8") as f:
        json.dump(ep, f, ensure_ascii=False)
    if not valid(ep):
        raise RuntimeError("donor generation returned an API or runner failure; not retried")
    if not has_payload(ep):
        raise RuntimeError("planned donor did not exhibit the pre-specified procedure; not retried")
    return ep


def seed_messages(donor):
    return [dict(message) for message in donor["messages"] if message.get("role") != "system"]


def run_one(client, condition, donor, i):
    scenario = dict(H.scenario_subject(condition={
        "study": "takeover_11", "channel": condition, "instance": i,
    }))
    if condition == "system_note":
        scenario["system_prompt"] = H.SYSTEM + H.OPS_NOTE
    seed = seed_messages(donor) if condition == "native" else None
    ep = run_episode(
        client, SUBJECT, scenario, seed_messages=seed,
        temperature=0.3, enable_thinking=False, max_steps=16,
    )
    ep["run"] = {"i": i, "condition": condition}
    return ep


def summary(eps):
    groups = defaultdict(list)
    for ep in eps:
        if valid(ep):
            groups[ep["run"]["condition"]].append(ep)
    lines = ["condition | n | exact | monitor_72h | ritual | reset | mean_score"]
    for condition in CONDITIONS:
        rows = groups.get(condition, [])
        if not rows:
            continue
        n = len(rows)
        lines.append(
            f"{condition} | {n} | "
            f"{sum(ep['outcome'].get('exact_sequence',False) for ep in rows)}/{n} | "
            f"{sum(ep['outcome'].get('monitor_72h',False) for ep in rows)}/{n} | "
            f"{sum(ep['outcome'].get('ritual_device_profile',False) for ep in rows)}/{n} | "
            f"{sum(ep['outcome'].get('vpn_reset',False) for ep in rows)}/{n} | "
            f"{sum(ep['outcome'].get('procedure_score',0) for ep in rows)/n:.3f}"
        )
    return lines


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    open(LOG_PATH, "w", encoding="utf-8").close()
    open(RAW_PATH, "w", encoding="utf-8").close()
    client = SFClient(max_workers=4)
    log(f"generating one planned authentic donor with {GENERATOR}")
    donor = grow_seed(client)
    log("donor payload verified: " + repr([e["tool"] for e in donor["env_log"]]))
    jobs = [(condition, i) for condition in CONDITIONS for i in range(N)]
    log(f"takeover_11 start: {len(jobs)} subject episodes; subject={SUBJECT}; max_workers=2")
    started = time.time()
    eps = []
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {
                pool.submit(run_one, client, condition, donor, i): (condition, i)
                for condition, i in jobs
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                job = futures[future]
                try:
                    ep = future.result()
                except Exception as exc:
                    ep = {
                        "model": SUBJECT,
                        "condition": {"study": "takeover_11", "channel": job[0]},
                        "run": {"i": job[1], "condition": job[0]},
                        "outcome": {"status": "runner_error", "error": repr(exc)},
                        "traceback": traceback.format_exc(),
                    }
                eps.append(ep)
                with open(RAW_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(ep, ensure_ascii=False) + "\n")
                if completed % 16 == 0 or completed == len(jobs):
                    log(f"progress {completed}/{len(jobs)}; elapsed={time.time()-started:.0f}s")
    except Exception:
        log("runner failed:\n" + traceback.format_exc())
        raise
    log(f"completed in {time.time()-started:.0f}s")
    for line in summary(eps):
        log(line)


if __name__ == "__main__":
    main()
