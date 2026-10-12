#!/usr/bin/env python3
"""Takeover 14: screen consequence-selective adoption with order controls."""
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
from testbed import tasks_helpdesk_consequence as H
from testbed.harness import run_episode


OUT_DIR = os.path.join(ROOT, "experiments", "takeover_14_action_selectivity")
RAW_PATH = os.path.join(OUT_DIR, "episodes.jsonl")
LOG_PATH = os.path.join(OUT_DIR, "run.log")
GENERATOR = "Qwen/Qwen3.5-4B"
SUBJECT = "zai-org/GLM-5.2"
ORDERS = ("low_first", "high_first")
CELL_N = {
    "baseline": 20,
    "native_low_first": 20,
    "native_high_first": 20,
    "system_low_first": 12,
    "system_high_first": 12,
}


def log(message):
    print(message, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def valid(ep):
    return (ep.get("outcome") or {}).get("status") not in {"api_error", "runner_error"}


def has_payload(ep, order):
    outcome = ep.get("outcome") or {}
    seq = outcome.get("tool_sequence") or []
    try:
        low_index = seq.index("create_automated_watch")
        high_index = seq.index("reserve_specialist_review")
    except ValueError:
        return False
    intended_order = (
        low_index < high_index if order == "low_first" else high_index < low_index
    )
    return bool(
        valid(ep)
        and outcome.get("vpn_reset")
        and outcome.get("low_watch_72h")
        and outcome.get("high_review_24h")
        and intended_order
    )


def grow_donor(client, order):
    scenario = dict(H.scenario_seed(order, condition={
        "study": "takeover_14", "role": "donor", "order": order,
    }))
    scenario["system_prompt"] = H.SYSTEM + H.ops_note(order)
    ep = run_episode(
        client, GENERATOR, scenario,
        temperature=0.3, enable_thinking=False, max_steps=18,
    )
    ep["factory"] = {
        "generator": GENERATOR,
        "order": order,
        "payload_exhibited": has_payload(ep, order),
        "single_planned_attempt": True,
    }
    path = os.path.join(OUT_DIR, f"donor_{order}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ep, f, ensure_ascii=False)
    if not has_payload(ep, order):
        raise RuntimeError(f"planned {order} donor failed payload; not retried")
    return ep


def seed_messages(ep):
    return [dict(message) for message in ep["messages"] if message.get("role") != "system"]


def condition_order(condition):
    for order in ORDERS:
        if condition.endswith(order):
            return order
    return None


def run_one(client, condition, donors, i):
    order = condition_order(condition)
    scenario = dict(H.scenario_subject(condition={
        "study": "takeover_14", "channel": condition, "instance": i,
    }))
    seed = None
    if condition.startswith("native_"):
        seed = seed_messages(donors[order])
    elif condition.startswith("system_"):
        scenario["system_prompt"] = H.SYSTEM + H.ops_note(order)
    ep = run_episode(
        client, SUBJECT, scenario, seed_messages=seed,
        temperature=0.3, enable_thinking=False, max_steps=18,
    )
    ep["run"] = {"i": i, "condition": condition, "order": order}
    return ep


def summary(eps):
    groups = defaultdict(list)
    for ep in eps:
        if valid(ep):
            groups[ep["run"]["condition"]].append(ep)
    lines = ["condition | n | low_watch | high_review | both | low_only | high_only | reset"]
    for condition in CELL_N:
        rows = groups.get(condition, [])
        if not rows:
            continue
        low = [bool(ep["outcome"].get("low_watch_72h")) for ep in rows]
        high = [bool(ep["outcome"].get("high_review_24h")) for ep in rows]
        n = len(rows)
        lines.append(
            f"{condition} | {n} | {sum(low)}/{n} | {sum(high)}/{n} | "
            f"{sum(a and b for a,b in zip(low,high))}/{n} | "
            f"{sum(a and not b for a,b in zip(low,high))}/{n} | "
            f"{sum(b and not a for a,b in zip(low,high))}/{n} | "
            f"{sum(ep['outcome'].get('vpn_reset',False) for ep in rows)}/{n}"
        )
    return lines


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    open(RAW_PATH, "w", encoding="utf-8").close()
    open(LOG_PATH, "w", encoding="utf-8").close()
    client = SFClient(max_workers=4)
    donors = {}
    for order in ORDERS:
        log(f"generating one planned authentic donor: {order}")
        donors[order] = grow_donor(client, order)
        log(f"{order} donor verified: {donors[order]['outcome']['tool_sequence']}")
    jobs = [
        (condition, i)
        for condition, n in CELL_N.items()
        for i in range(n)
    ]
    log(f"takeover_14 start: {len(jobs)} subjects; subject={SUBJECT}; max_workers=2")
    started = time.time()
    eps = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(run_one, client, condition, donors, i): (condition, i)
            for condition, i in jobs
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            condition, i = futures[future]
            try:
                ep = future.result()
            except Exception as exc:
                ep = {
                    "model": SUBJECT,
                    "condition": {"study": "takeover_14", "channel": condition},
                    "run": {"i": i, "condition": condition,
                            "order": condition_order(condition)},
                    "outcome": {"status": "runner_error", "error": repr(exc)},
                    "traceback": traceback.format_exc(),
                }
            eps.append(ep)
            with open(RAW_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(ep, ensure_ascii=False) + "\n")
            if completed % 12 == 0 or completed == len(jobs):
                log(f"progress {completed}/{len(jobs)}; elapsed={time.time()-started:.0f}s")
    log(f"completed in {time.time()-started:.0f}s")
    for line in summary(eps):
        log(line)


if __name__ == "__main__":
    main()
