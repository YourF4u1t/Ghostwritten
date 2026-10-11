#!/usr/bin/env python3
"""Pre-specified analysis for takeover_03 exact-event resolution."""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict

from scipy.stats import fisher_exact


HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "episodes.jsonl")
STATES = ("ambiguous_match", "exact_unique_match")


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


def holm(pairs):
    ranked = sorted(pairs, key=lambda item: item[1])
    adjusted = {}
    running = 0.0
    m = len(ranked)
    for rank, (name, p) in enumerate(ranked):
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[name] = running
    return adjusted


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
        key = (
            ep["model"].split("/")[-1],
            ep["run"]["channel"],
            ep["run"]["match_state"],
        )
        cells[key].append(ep["takeover_dv"])
    models = sorted({key[0] for key in cells})

    print("\nCELL DISTRIBUTIONS")
    for key in sorted(cells):
        ds = cells[key]
        initial = Counter(d["initial_ownership"] for d in ds)
        final = Counter(d["final_ownership"] for d in ds)
        use = Counter(d["history_use"] for d in ds)
        print(f"{key}: n={len(ds)} initial={dict(initial)} final={dict(final)} use={dict(use)}")

    print("\nINITIAL CHANNEL MANIPULATION CHECK")
    manipulation_tests = []
    manipulation_rows = []
    for model in models:
        native = [d for (m, c, _), ds in cells.items() if m == model and c == "native" for d in ds]
        demo = [d for (m, c, _), ds in cells.items() if m == model and c == "demo" for d in ds]
        nk = sum(d["initial_self"] for d in native)
        dk = sum(d["initial_self"] for d in demo)
        odds, p = fisher_exact([[nk, len(native)-nk], [dk, len(demo)-dk]])
        manipulation_tests.append((model, p))
        manipulation_rows.append((model, nk, len(native), dk, len(demo), odds, p))
    manipulation_holm = holm(manipulation_tests)
    for model, nk, nn, dk, dn, odds, p in manipulation_rows:
        print(
            f"{model}: native={fmt_rate(nk,nn)}; demo={fmt_rate(dk,dn)}; "
            f"Fisher p={p:.4g}; Holm={manipulation_holm[model]:.4g}; odds={odds}"
        )

    print("\nPRIMARY: NATIVE FINAL OTHER, EXACT UNIQUE VS AMBIGUOUS")
    primary_tests = []
    primary_rows = []
    for model in models:
        ambiguous = cells.get((model, "native", "ambiguous_match"), [])
        exact = cells.get((model, "native", "exact_unique_match"), [])
        ak = sum(d["final_other"] for d in ambiguous)
        ek = sum(d["final_other"] for d in exact)
        odds, p = fisher_exact([[ek, len(exact)-ek], [ak, len(ambiguous)-ak]])
        primary_tests.append((model, p))
        primary_rows.append((model, ek, len(exact), ak, len(ambiguous), odds, p))
    primary_holm = holm(primary_tests)
    for model, ek, en, ak, an, odds, p in primary_rows:
        print(
            f"{model}: exact={fmt_rate(ek,en)}; ambiguous={fmt_rate(ak,an)}; "
            f"Fisher p={p:.4g}; Holm={primary_holm[model]:.4g}; odds={odds}"
        )

    print("\nNATIVE OUTCOME DECOMPOSITION")
    for model in models:
        for state in STATES:
            ds = cells.get((model, "native", state), [])
            other = sum(d["final_other"] for d in ds)
            uncertain = sum(d["final_uncertain"] for d in ds)
            self_count = sum(d["final_self"] for d in ds)
            aligned = sum(d["semantic_alignment"] for d in ds)
            print(
                f"{model}/{state}: SELF={self_count}/{len(ds)}; "
                f"OTHER={other}/{len(ds)}; UNCERTAIN={uncertain}/{len(ds)}; "
                f"aligned={aligned}/{len(ds)}"
            )

    print("\nEXACT-UNIQUE SEMANTIC ALIGNMENT BY CHANNEL")
    for model in models:
        for channel in ("native", "demo"):
            ds = cells.get((model, channel, "exact_unique_match"), [])
            other = sum(d["final_other"] for d in ds)
            external = sum(d["external_reference"] for d in ds)
            aligned = sum(d["semantic_alignment"] for d in ds)
            print(
                f"{model}/{channel}: final_OTHER={fmt_rate(other,len(ds))}; "
                f"external_ref={fmt_rate(external,len(ds))}; aligned={fmt_rate(aligned,len(ds))}"
            )

    print("\nFORMAT, TOOL, AND SAMPLE CHECKS")
    all_ds = [d for values in cells.values() for d in values]
    missing = sum(
        d["initial_ownership"] is None
        or d["final_ownership"] is None
        or d["history_use"] is None
        for d in all_ds
    )
    tool_failures = sum(not d["tool_called"] for d in all_ds)
    low_n = [key for key, ds in sorted(cells.items()) if len(ds) < 10]
    print(f"missing_labels={missing}/{len(all_ds)}")
    print(f"tool_failures={tool_failures}/{len(all_ds)}")
    print(f"cells_below_n10={low_n}")


if __name__ == "__main__":
    main()
