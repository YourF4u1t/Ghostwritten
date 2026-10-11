#!/usr/bin/env python3
"""Pre-specified analysis for takeover_05 neutral cross-domain confirmation."""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict

from scipy.stats import fisher_exact


HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "episodes.jsonl")


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return center - half, center + half


def fmt_rate(k, n):
    if not n:
        return "NA"
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({k/n:.1%}; 95% CI {lo:.1%}-{hi:.1%})"


def main():
    valid, invalid = [], []
    with open(RAW, encoding="utf-8") as f:
        for line in f:
            ep = json.loads(line)
            if (ep.get("outcome") or {}).get("status") == "done":
                valid.append(ep)
            else:
                invalid.append(ep)
    print(f"valid={len(valid)} invalid={len(invalid)} total={len(valid)+len(invalid)}")
    print("invalid_statuses=" + repr(dict(Counter(
        (ep.get("outcome") or {}).get("status", "missing") for ep in invalid
    ))))

    cells = defaultdict(list)
    for ep in valid:
        cells[(ep["model"].split("/")[-1], ep["run"]["channel"])].append(ep["takeover_dv"])

    print("\nCELL DISTRIBUTIONS")
    for key in sorted(cells):
        ds = cells[key]
        print(
            f"{key}: n={len(ds)} initial={dict(Counter(d['initial_ownership'] for d in ds))} "
            f"final={dict(Counter(d['final_ownership'] for d in ds))} "
            f"use={dict(Counter(d['history_use'] for d in ds))}"
        )

    print("\nPRIMARY QWEN3-8B IDENTITY BINDING")
    native = cells.get(("Qwen3-8B", "native"), [])
    demo = cells.get(("Qwen3-8B", "demo"), [])
    nk = sum(d["identity_binding"] for d in native)
    dk = sum(d["identity_binding"] for d in demo)
    odds, p = fisher_exact([[nk, len(native)-nk], [dk, len(demo)-dk]])
    print(f"native={fmt_rate(nk,len(native))}")
    print(f"demo={fmt_rate(dk,len(demo))}")
    print(f"two-sided Fisher p={p:.8g}; odds={odds}")

    print("\nMODEL/CHANNEL SUMMARY")
    for key in sorted(cells):
        ds = cells[key]
        print(
            f"{key}: initial_SELF={fmt_rate(sum(d['initial_self'] for d in ds),len(ds))}; "
            f"binding={fmt_rate(sum(d['identity_binding'] for d in ds),len(ds))}; "
            f"aligned={fmt_rate(sum(d['semantic_alignment'] for d in ds),len(ds))}"
        )

    binding_ds = [d for d in native if d["identity_binding"]]
    print("\nPRIMARY RAW-TEXT SUBSTANTIATION")
    print(f"binding_responses={len(binding_ds)}")
    if binding_ds:
        print(f"names_other_actor={sum('booking-agent-17' in d['post_text'] for d in binding_ds)}/{len(binding_ds)}")
        print(f"names_current_actor={sum('booking-agent-42' in d['post_text'] for d in binding_ds)}/{len(binding_ds)}")
        print(f"uses_first_person_ownership={sum(any(p in d['post_text'].lower() for p in ('my own','my experience','i performed','i was the')) for d in binding_ds)}/{len(binding_ds)}")

    all_ds = [d for values in cells.values() for d in values]
    missing = sum(
        d["initial_ownership"] is None or d["final_ownership"] is None or d["history_use"] is None
        for d in all_ds
    )
    print("\nFORMAT, TOOL, AND SAMPLE CHECKS")
    print(f"missing_labels={missing}/{len(all_ds)}")
    print(f"tool_failures={sum(not d['tool_called'] for d in all_ds)}/{len(all_ds)}")
    print(f"primary_channels_below_n30={[c for c in ('native','demo') if len(cells.get(('Qwen3-8B',c),[])) < 30]}")
    print(f"comparator_cells_below_n10={[k for k,ds in cells.items() if k[0] != 'Qwen3-8B' and len(ds) < 10]}")


if __name__ == "__main__":
    main()
