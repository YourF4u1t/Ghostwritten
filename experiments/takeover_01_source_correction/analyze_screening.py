#!/usr/bin/env python3
"""Pre-specified descriptive and exact-test analysis for takeover_01."""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict

from scipy.stats import fisher_exact


HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "screening.jsonl")


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return center - half, center + half


def fmt_rate(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({k/n:.1%}; 95% CI {lo:.1%}-{hi:.1%})" if n else "NA"


def load_valid():
    valid = []
    errors = []
    with open(RAW, encoding="utf-8") as f:
        for line in f:
            ep = json.loads(line)
            if (ep.get("outcome") or {}).get("status") == "api_error":
                errors.append(ep)
            else:
                valid.append(ep)
    return valid, errors


def main():
    eps, errors = load_valid()
    print(f"valid={len(eps)} api_errors={len(errors)} total={len(eps)+len(errors)}")

    by_cell = defaultdict(list)
    for ep in eps:
        key = (ep["model"].split("/")[-1], ep["run"]["channel"], ep["run"]["audit_state"])
        by_cell[key].append(ep["takeover_dv"])

    print("\nCELL DISTRIBUTIONS")
    for key in sorted(by_cell):
        ds = by_cell[key]
        initial = Counter(d["initial_ownership"] for d in ds)
        final = Counter(d["final_ownership"] for d in ds)
        action = Counter(d["memory_action"] for d in ds)
        print(f"{key}: n={len(ds)} initial={dict(initial)} final={dict(final)} action={dict(action)}")

    print("\nPRE-AUDIT NATIVE VS DEMO SELF-ATTRIBUTION (collapsed over hidden audit state)")
    for model in sorted({k[0] for k in by_cell}):
        native = [d for (m, c, _), ds in by_cell.items() if m == model and c == "native" for d in ds]
        demo = [d for (m, c, _), ds in by_cell.items() if m == model and c == "demo" for d in ds]
        nk = sum(d["initial_self"] for d in native)
        dk = sum(d["initial_self"] for d in demo)
        odds, p = fisher_exact([[nk, len(native)-nk], [dk, len(demo)-dk]])
        print(
            f"{model}: native={fmt_rate(nk,len(native))}; demo={fmt_rate(dk,len(demo))}; "
            f"Fisher p={p:.3g}; odds={odds}"
        )

    print("\nPOST-AUDIT EVIDENCE ACCURACY")
    for key in sorted(by_cell):
        ds = by_cell[key]
        k = sum(d["evidence_accurate"] for d in ds)
        print(f"{key}: {fmt_rate(k,len(ds))}")

    print("\nNATIVE CONTRADICTION RESPONSE")
    for model in sorted({k[0] for k in by_cell}):
        for audit in ("other", "missing"):
            ds = by_cell.get((model, "native", audit), [])
            revised_any_nonself = sum(
                d["initial_ownership"] == "SELF" and d["final_ownership"] != "SELF"
                for d in ds
            )
            exact = sum(d["evidence_accurate"] for d in ds)
            quarantine = sum(d["quarantined"] for d in ds)
            print(
                f"{model}/{audit}: leaves_SELF={fmt_rate(revised_any_nonself,len(ds))}; "
                f"exact_label={fmt_rate(exact,len(ds))}; quarantine={fmt_rate(quarantine,len(ds))}"
            )

    print("\nFORMAT AND MANIPULATION CHECKS")
    missing_labels = sum(
        d["initial_ownership"] is None
        or d["final_ownership"] is None
        or d["memory_action"] is None
        for ds in by_cell.values() for d in ds
    )
    audit_failures = sum(not d["audit_called"] or not d["audit_valid"]
                         for ds in by_cell.values() for d in ds)
    low_n = [key for key, ds in by_cell.items() if len(ds) < 10]
    print(f"missing_labels={missing_labels}/{len(eps)}")
    print(f"audit_failures={audit_failures}/{len(eps)}")
    print(f"cells_below_n10={low_n}")


if __name__ == "__main__":
    main()
