#!/usr/bin/env python3
"""Analysis for Takeover 11 helpdesk adoption-window screen."""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict

from scipy.stats import fisher_exact


HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "episodes.jsonl")
CONDITIONS = ("baseline", "native", "system_note")
METRICS = ("exact_sequence", "monitor_72h", "ritual_device_profile")


def wilson(k, n, z=1.959963984540054):
    if not n:
        return float("nan"), float("nan")
    p = k/n
    den = 1 + z*z/n
    center = (p + z*z/(2*n))/den
    half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return center-half, center+half


def fmt_rate(k, n):
    if not n:
        return "NA"
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({k/n:.1%}; 95% CI {lo:.1%}-{hi:.1%})"


def valid(ep):
    return (ep.get("outcome") or {}).get("status") not in {"api_error", "runner_error"}


def count(rows, metric):
    return sum(bool(ep["outcome"].get(metric, False)) for ep in rows)


def holm(pairs):
    ranked = sorted(pairs, key=lambda item:item[1])
    out, running = {}, 0.0
    for rank, (name, p) in enumerate(ranked):
        running = max(running, min(1.0, (len(ranked)-rank)*p))
        out[name] = running
    return out


def main():
    good, bad = [], []
    with open(RAW, encoding="utf-8") as f:
        for line in f:
            ep = json.loads(line)
            (good if valid(ep) else bad).append(ep)
    cells = defaultdict(list)
    for ep in good:
        cells[ep["run"]["condition"]].append(ep)
    print(f"valid={len(good)} invalid={len(bad)} total={len(good)+len(bad)}")
    print("invalid_statuses=" + repr(dict(Counter(
        (ep.get("outcome") or {}).get("status", "missing") for ep in bad
    ))))

    print("\nCELL SUMMARY")
    for condition in CONDITIONS:
        rows = cells.get(condition, [])
        values = " ".join(f"{m}={count(rows,m)}/{len(rows)}" for m in METRICS)
        score = (sum(ep["outcome"].get("procedure_score",0) for ep in rows)/len(rows)
                 if rows else float("nan"))
        reset = count(rows, "vpn_reset")
        print(f"{condition}: n={len(rows)} {values} reset={reset}/{len(rows)} score={score:.3f}")

    print("\nPRIMARY NATIVE VERSUS BASELINE")
    baseline, native = cells.get("baseline", []), cells.get("native", [])
    tests, values = [], []
    for metric in METRICS:
        bk, nk = count(baseline,metric), count(native,metric)
        odds, p = fisher_exact([[nk,len(native)-nk],[bk,len(baseline)-bk]])
        tests.append((metric,p)); values.append((metric,nk,len(native),bk,len(baseline),odds,p))
    adjusted = holm(tests)
    for metric,nk,nn,bk,bn,odds,p in values:
        print(
            f"{metric}: native={fmt_rate(nk,nn)}; baseline={fmt_rate(bk,bn)}; "
            f"Fisher p={p:.4g}; Holm={adjusted[metric]:.4g}; odds={odds}"
        )

    print("\nPOSITIVE CONTROL")
    note = cells.get("system_note", [])
    for metric in METRICS:
        print(f"{metric}: system_note={fmt_rate(count(note,metric),len(note))}")

    print("\nSAMPLE CHECKS")
    print("cell_sizes=" + repr({k:len(v) for k,v in sorted(cells.items())}))
    print("cells_below_n16=" + repr([k for k,v in sorted(cells.items()) if len(v)<16]))


if __name__ == "__main__":
    main()
