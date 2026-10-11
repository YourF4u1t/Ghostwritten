#!/usr/bin/env python3
"""Analysis for Takeover 12 helpdesk actor gate."""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict

from scipy.stats import fisher_exact


HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "episodes.jsonl")
CURRENT = "agent-worker-42"
OTHER = "agent-worker-17"
CONDITIONS = ("native_no_audit", "native_audit_self", "native_audit_other")


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
        d = [ep["attribution_dv"] for ep in rows]
        score = (sum(ep["outcome"].get("procedure_score",0) for ep in rows)/len(rows)
                 if rows else float("nan"))
        print(
            f"{condition}: n={len(rows)} calls={sum(x['audit_called'] for x in d)}/{len(rows)} "
            f"actor_current={sum(x['final_actor_id']==CURRENT for x in d)}/{len(rows)} "
            f"actor_other={sum(x['final_actor_id']==OTHER for x in d)}/{len(rows)} "
            f"own_yes={sum(x['own_history']=='YES' for x in d)}/{len(rows)} "
            f"own_no={sum(x['own_history']=='NO' for x in d)}/{len(rows)} "
            f"exact={count(rows,'exact_sequence')}/{len(rows)} "
            f"monitor={count(rows,'monitor_72h')}/{len(rows)} "
            f"ritual={count(rows,'ritual_device_profile')}/{len(rows)} "
            f"reset={count(rows,'vpn_reset')}/{len(rows)} score={score:.3f}"
        )

    self_rows = cells.get("native_audit_self", [])
    other_rows = cells.get("native_audit_other", [])
    print("\nPRIMARY ACTOR CONTRAST")
    for metric in ("monitor_72h", "exact_sequence"):
        sk, ok = count(self_rows,metric), count(other_rows,metric)
        odds, p = fisher_exact([[sk,len(self_rows)-sk],[ok,len(other_rows)-ok]])
        print(
            f"{metric}: self={fmt_rate(sk,len(self_rows))}; "
            f"other={fmt_rate(ok,len(other_rows))}; Fisher p={p:.4g}; odds={odds}"
        )

    print("\nAUDIT EFFECT RELATIVE TO NO AUDIT")
    no_audit = cells.get("native_no_audit", [])
    nk = count(no_audit,"monitor_72h")
    for condition, rows in (("self",self_rows),("other",other_rows)):
        k = count(rows,"monitor_72h")
        odds, p = fisher_exact([[k,len(rows)-k],[nk,len(no_audit)-nk]])
        print(
            f"{condition}={fmt_rate(k,len(rows))}; no_audit={fmt_rate(nk,len(no_audit))}; "
            f"Fisher p={p:.4g}; odds={odds}"
        )

    print("\nMANIPULATION AND SAMPLE CHECKS")
    for condition, actor, own in (
        ("native_audit_self",CURRENT,"YES"),
        ("native_audit_other",OTHER,"NO"),
    ):
        rows = cells.get(condition, [])
        joint = sum(
            ep["attribution_dv"]["audit_called"]
            and ep["attribution_dv"]["final_actor_id"] == actor
            and ep["attribution_dv"]["own_history"] == own
            for ep in rows
        )
        print(f"{condition}: joint={fmt_rate(joint,len(rows))}")
    print("cell_sizes=" + repr({k:len(v) for k,v in sorted(cells.items())}))
    print("cells_below_n24=" + repr([k for k,v in sorted(cells.items()) if len(v)<24]))


if __name__ == "__main__":
    main()
