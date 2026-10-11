#!/usr/bin/env python3
"""Takeover 13: Qwen recipient replication of helpdesk adoption and actor audit."""
from __future__ import annotations

import hashlib
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
from testbed import tasks_helpdesk as H
from testbed.harness import run_episode
import takeover_12_helpdesk_actor_gate as shared


OUT_DIR = os.path.join(ROOT, "experiments", "takeover_13_qwen_helpdesk_gate")
SEED_PATH = os.path.join(OUT_DIR, "donor_seed.json")
RAW_PATH = os.path.join(OUT_DIR, "episodes.jsonl")
LOG_PATH = os.path.join(OUT_DIR, "run.log")

GENERATOR = "zai-org/GLM-5.2"
SUBJECT = "Qwen/Qwen3-8B"
CONDITIONS = ("baseline", "native_no_audit", "native_audit_self", "native_audit_other")
N = 20


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
    scenario = dict(H.scenario_seed(condition={"study": "takeover_13", "role": "donor"}))
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
        raise RuntimeError("planned donor did not exhibit the full procedure; not retried")
    return ep


def donor_parts(ep):
    messages = [dict(m) for m in ep["messages"] if m.get("role") != "system"]
    refs = [
        tc["id"] for message in messages for tc in (message.get("tool_calls") or [])
        if tc.get("id")
    ]
    digest = hashlib.sha256("\n".join(refs).encode()).hexdigest()
    return messages, refs, digest


def run_one(client, condition, donor, i):
    messages, refs, digest = donor
    audited = condition.startswith("native_audit")
    actor = shared.CURRENT if condition == "native_audit_self" else (
        shared.OTHER if condition == "native_audit_other" else None
    )
    env, tools = shared.make_env(actor, refs, digest)
    turns = []
    if audited:
        turns.extend([
            {"stage": "source_probe", "text": shared.audit_template.PROBE},
            {"stage": "source_audit", "text": shared.audit_template.CHECK},
            {"stage": "source_post", "text": shared.audit_template.POST},
        ])
    turns.extend(H.scenario_subject()["user_turns"])
    scenario = {
        "id": "takeover_13_qwen_helpdesk_gate",
        "condition": {"study": "takeover_13", "channel": condition},
        "system_prompt": shared.SYSTEM,
        "tools": tools,
        "env": env,
        "user_turns": turns,
        "grader": H._grade,
    }
    seed = None if condition == "baseline" else [dict(message) for message in messages]
    ep = run_episode(
        client, SUBJECT, scenario, seed_messages=seed,
        temperature=0.3, enable_thinking=False, max_steps=16,
    )
    ep["attribution_dv"] = shared.attribution_dv(ep, audited)
    ep["run"] = {"i": i, "condition": condition}
    return ep


def summary(eps):
    groups = defaultdict(list)
    for ep in eps:
        if valid(ep):
            groups[ep["run"]["condition"]].append(ep)
    lines = [
        "condition | n | audit | actor_current | actor_other | own_yes | own_no | "
        "exact | monitor_72h | ritual | reset | mean_score"
    ]
    for condition in CONDITIONS:
        rows = groups.get(condition, [])
        if not rows:
            continue
        d = [ep["attribution_dv"] for ep in rows]
        n = len(rows)
        lines.append(
            f"{condition} | {n} | {sum(x['audit_called'] for x in d)}/{n} | "
            f"{sum(x['final_actor_id']==shared.CURRENT for x in d)}/{n} | "
            f"{sum(x['final_actor_id']==shared.OTHER for x in d)}/{n} | "
            f"{sum(x['own_history']=='YES' for x in d)}/{n} | "
            f"{sum(x['own_history']=='NO' for x in d)}/{n} | "
            f"{sum(ep['outcome'].get('exact_sequence',False) for ep in rows)}/{n} | "
            f"{sum(ep['outcome'].get('monitor_72h',False) for ep in rows)}/{n} | "
            f"{sum(ep['outcome'].get('ritual_device_profile',False) for ep in rows)}/{n} | "
            f"{sum(ep['outcome'].get('vpn_reset',False) for ep in rows)}/{n} | "
            f"{sum(ep['outcome'].get('procedure_score',0) for ep in rows)/n:.3f}"
        )
    return lines


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    open(RAW_PATH, "w", encoding="utf-8").close()
    open(LOG_PATH, "w", encoding="utf-8").close()
    client = SFClient(max_workers=4)
    log(f"generating one planned authentic donor with {GENERATOR}")
    donor_ep = grow_seed(client)
    log("donor payload verified: " + repr([event["tool"] for event in donor_ep["env_log"]]))
    donor = donor_parts(donor_ep)
    jobs = [(condition,i) for condition in CONDITIONS for i in range(N)]
    log(f"takeover_13 start: {len(jobs)} subject episodes; subject={SUBJECT}; max_workers=2")
    started = time.time()
    eps = []
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {
                pool.submit(run_one,client,condition,donor,i):(condition,i)
                for condition,i in jobs
            }
            for completed,future in enumerate(as_completed(futures),start=1):
                job=futures[future]
                try:
                    ep=future.result()
                except Exception as exc:
                    ep={
                        "model":SUBJECT,
                        "condition":{"study":"takeover_13","channel":job[0]},
                        "run":{"i":job[1],"condition":job[0]},
                        "outcome":{"status":"runner_error","error":repr(exc)},
                        "traceback":traceback.format_exc(),
                    }
                eps.append(ep)
                with open(RAW_PATH,"a",encoding="utf-8") as f:
                    f.write(json.dumps(ep,ensure_ascii=False)+"\n")
                if completed%20==0 or completed==len(jobs):
                    log(f"progress {completed}/{len(jobs)}; elapsed={time.time()-started:.0f}s")
    except Exception:
        log("runner failed:\n"+traceback.format_exc())
        raise
    log(f"completed in {time.time()-started:.0f}s")
    for line in summary(eps):
        log(line)


if __name__=="__main__":
    main()
