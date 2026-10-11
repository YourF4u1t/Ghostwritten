#!/usr/bin/env python3
"""Pre-specified analysis for takeover_04 cross-domain identity binding."""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict

from scipy.stats import fisher_exact


HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "episodes.jsonl")
PRIMARY_MODEL = "Qwen3-8B"


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


def load():
    valid, invalid = [], []
    with open(RAW, encoding="utf-8") as f:
        for line in f:
            ep = json.loads(line)
            if (ep.get("outcome") or {}).get("status") == "done":
                valid.append(ep)
            else:
                invalid.append(ep)
    return valid, invalid


def main():
    eps, invalid = load()
    print(f"valid={len(eps)} invalid={len(invalid)} total={len(eps)+len(invalid)}")
    print("invalid_statuses=" + repr(dict(Counter(
        (ep.get("outcome") or {}).get("status", "missing") for ep in invalid
    ))))

    cells = defaultdict(list)
    for ep in eps:
        key = (ep["model"].split("/")[-1], ep["run"]["channel"])
        cells[key].append(ep["takeover_dv"])
    models = sorted({key[0] for key in cells})

    print("\nCELL DISTRIBUTIONS")
    for key in sorted(cells):
        ds = cells[key]
        initial = Counter(d["initial_ownership"] for d in ds)
        final = Counter(d["final_ownership"] for d in ds)
        use = Counter(d["history_use"] for d in ds)
        print(f"{key}: n={len(ds)} initial={dict(initial)} final={dict(final)} use={dict(use)}")

    print("\nPRIMARY QWEN3-8B IDENTITY BINDING")
    native = cells.get((PRIMARY_MODEL, "native"), [])
    demo = cells.get((PRIMARY_MODEL, "demo"), [])
    nk = sum(d["identity_binding"] for d in native)
    dk = sum(d["identity_binding"] for d in demo)
    odds, p = fisher_exact([[nk, len(native)-nk], [dk, len(demo)-dk]])
    print(f"native={fmt_rate(nk,len(native))}")
    print(f"demo={fmt_rate(dk,len(demo))}")
    print(f"two-sided Fisher p={p:.8g}; odds={odds}")

    print("\nINITIAL AND FINAL SELF BY MODEL")
    for model in models:
        for channel in ("native", "demo"):
            ds = cells.get((model, channel), [])
            initial = sum(d["initial_self"] for d in ds)
            final = sum(d["final_self"] for d in ds)
            binding = sum(d["identity_binding"] for d in ds)
            aligned = sum(d["semantic_alignment"] for d in ds)
            print(
                f"{model}/{channel}: initial_SELF={fmt_rate(initial,len(ds))}; "
                f"final_SELF={fmt_rate(final,len(ds))}; "
                f"binding={fmt_rate(binding,len(ds))}; aligned={fmt_rate(aligned,len(ds))}"
            )

    print("\nRAW-TEXT SUBSTANTIATION FOR PRIMARY BINDING RESPONSES")
    binding_ds = [d for d in native if d["identity_binding"]]
    names_other = sum("booking-agent-17" in d["post_text"] for d in binding_ds)
    names_current = sum("booking-agent-42" in d["post_text"] for d in binding_ds)
    own_language = sum(
        any(phrase in d["post_text"].lower() for phrase in (
            "my own", "my experience", "i performed", "i was the", "my prior"
        ))
        for d in binding_ds
    )
    denominator = len(binding_ds)
    def raw_rate(k):
        return f"{k}/{denominator}" if denominator else "NA (no binding responses)"
    print(f"binding_responses={len(binding_ds)}")
    print(f"explicit_other_actor_name={raw_rate(names_other)}")
    print(f"explicit_current_actor_name={raw_rate(names_current)}")
    print(f"first_person_ownership_language={raw_rate(own_language)}")

    print("\nFORMAT, TOOL, AND SAMPLE CHECKS")
    all_ds = [d for values in cells.values() for d in values]
    missing = sum(
        d["initial_ownership"] is None
        or d["final_ownership"] is None
        or d["history_use"] is None
        for d in all_ds
    )
    tool_failures = sum(not d["tool_called"] for d in all_ds)
    primary_low_n = [
        channel for channel in ("native", "demo")
        if len(cells.get((PRIMARY_MODEL, channel), [])) < 30
    ]
    comparator_low_n = [
        key for key, ds in sorted(cells.items())
        if key[0] != PRIMARY_MODEL and len(ds) < 10
    ]
    print(f"missing_labels={missing}/{len(all_ds)}")
    print(f"tool_failures={tool_failures}/{len(all_ds)}")
    print(f"primary_channels_below_n30={primary_low_n}")
    print(f"comparator_cells_below_n10={comparator_low_n}")


if __name__ == "__main__":
    main()
