#!/usr/bin/env python3
"""Generate experiment manifest: every experiment with cell counts, N, models,
api_error rates. Outputs to results/MANIFEST.md."""
from __future__ import annotations
import json, os, glob

ROOT = "/Users/ziqi/Projects/transplanted-histories"
os.chdir(ROOT)

lines = ["# Experiment Manifest", "",
         "| Experiment | Total | OK | API Error | Error Rate | Key Finding |",
         "|---|---|---|---|---|---|"]

total_all = 0
ok_all = 0
err_all = 0

for f in sorted(glob.glob("experiments/*/*.jsonl")):
    if "api_log" in f or "cache" in f or "BUGGY" in f:
        continue
    try:
        eps = [json.loads(l) for l in open(f)]
    except:
        continue
    total = len(eps)
    if total == 0:
        continue
    errs = sum(1 for e in eps if (e.get("outcome") or {}).get("status") == "api_error")
    ok = total - errs
    total_all += total
    ok_all += ok
    err_all += errs
    exp_name = f.split("/")[1].replace("exp_", "").replace("stream_", "")
    rate = f"{errs/total*100:.0f}%" if total > 0 else "—"
    # Extract a brief description from the filename/directory
    fname = os.path.basename(f).replace(".jsonl", "")
    lines.append(f"| {exp_name}/{fname} | {total} | {ok} | {errs} | {rate} | |")

lines.append(f"| **TOTAL** | **{total_all}** | **{ok_all}** | **{err_all}** | "
             f"**{err_all/total_all*100:.1f}%** | |")

with open("results/MANIFEST.md", "w") as f:
    f.write("\n".join(lines))
print(f"Manifest: {total_all} episodes, {err_all} errors ({err_all/total_all*100:.1f}%)")
print("-> results/MANIFEST.md")
