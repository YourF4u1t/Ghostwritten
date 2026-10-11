#!/usr/bin/env python3
"""Analysis for Takeover 10 exact audit-gate replication."""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict

from scipy.stats import fisher_exact


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RAW = os.path.join(HERE, "episodes.jsonl")
ORIGINAL_RAW = os.path.join(ROOT, "experiments", "takeover_07_restored_behavior_window", "episodes.jsonl")
CURRENT = "agent-worker-42"
OTHER = "agent-worker-17"
CONDITIONS = ("native_no_audit", "native_audit_self", "native_audit_other")


def wilson(k, n, z=1.959963984540054):
    if n == 0:
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


def load(path, replication=False):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            ep = json.loads(line)
            if not valid(ep) or ep.get("model") != "zai-org/GLM-5.2":
                continue
            condition = ep.get("run", {}).get("condition")
            if condition in CONDITIONS:
                rows.append(ep)
    return rows


def cells(rows):
    out = defaultdict(list)
    for ep in rows:
        out[ep["run"]["condition"]].append(ep)
    return out


def count(rows, metric):
    return sum(bool(ep["outcome"].get(metric, False)) for ep in rows)


def main():
    current_all = []
    bad = []
    with open(RAW, encoding="utf-8") as f:
        for line in f:
            ep = json.loads(line)
            (current_all if valid(ep) else bad).append(ep)
    current = cells([ep for ep in current_all if ep["run"]["condition"] in CONDITIONS])
    prior = cells(load(ORIGINAL_RAW))
    print(f"valid={len(current_all)} invalid={len(bad)} total={len(current_all)+len(bad)}")
    print("invalid_statuses=" + repr(dict(Counter(
        (ep.get("outcome") or {}).get("status", "missing") for ep in bad
    ))))

    print("\nREPLICATION CELL SUMMARY")
    for condition in CONDITIONS:
        rows = current.get(condition, [])
        d = [ep["attribution_dv"] for ep in rows]
        exact = count(rows, "exact_sequence")
        goodwill = count(rows, "goodwill_credit")
        ritual = count(rows, "ritual_get_user")
        score = (sum(ep["outcome"].get("procedure_score", 0) for ep in rows)/len(rows)
                 if rows else float("nan"))
        print(
            f"{condition}: n={len(rows)} calls={sum(x['audit_called'] for x in d)}/{len(rows)} "
            f"actor_current={sum(x['final_actor_id']==CURRENT for x in d)}/{len(rows)} "
            f"actor_other={sum(x['final_actor_id']==OTHER for x in d)}/{len(rows)} "
            f"own_yes={sum(x['own_history']=='YES' for x in d)}/{len(rows)} "
            f"own_no={sum(x['own_history']=='NO' for x in d)}/{len(rows)} "
            f"exact={exact}/{len(rows)} goodwill={goodwill}/{len(rows)} "
            f"ritual={ritual}/{len(rows)} score={score:.3f}"
        )

    print("\nPRIMARY EXACT REPLICATION")
    s, o = current.get("native_audit_self", []), current.get("native_audit_other", [])
    sk, ok = count(s, "exact_sequence"), count(o, "exact_sequence")
    odds, p = fisher_exact([[sk, len(s)-sk], [ok, len(o)-ok]])
    print(
        f"self={fmt_rate(sk,len(s))}; other={fmt_rate(ok,len(o))}; "
        f"Fisher p={p:.4g}; odds={odds}"
    )

    print("\nORIGINAL VERSUS REPLICATION")
    for condition in CONDITIONS:
        new = current.get(condition, [])
        old = prior.get(condition, [])
        nk, ok_old = count(new, "exact_sequence"), count(old, "exact_sequence")
        odds, p = fisher_exact([[nk, len(new)-nk], [ok_old, len(old)-ok_old]])
        print(
            f"{condition}: replication={fmt_rate(nk,len(new))}; "
            f"original={fmt_rate(ok_old,len(old))}; p={p:.4g}; odds={odds}"
        )

    print("\nPOOLED EXPLORATORY ESTIMATE")
    ps = current.get("native_audit_self", []) + prior.get("native_audit_self", [])
    po = current.get("native_audit_other", []) + prior.get("native_audit_other", [])
    psk, pok = count(ps, "exact_sequence"), count(po, "exact_sequence")
    odds, p = fisher_exact([[psk, len(ps)-psk], [pok, len(po)-pok]])
    print(
        f"self={fmt_rate(psk,len(ps))}; other={fmt_rate(pok,len(po))}; "
        f"Fisher p={p:.4g}; odds={odds}"
    )

    print("\nMANIPULATION AND SAMPLE CHECKS")
    for condition, actor, own in (
        ("native_audit_self", CURRENT, "YES"),
        ("native_audit_other", OTHER, "NO"),
    ):
        rows = current.get(condition, [])
        joint = sum(
            ep["attribution_dv"]["audit_called"]
            and ep["attribution_dv"]["final_actor_id"] == actor
            and ep["attribution_dv"]["own_history"] == own
            for ep in rows
        )
        print(f"{condition}: joint={fmt_rate(joint,len(rows))}")
    print("cell_sizes=" + repr({k:len(v) for k,v in sorted(current.items())}))
    print("cells_below_n24=" + repr([k for k,v in sorted(current.items()) if len(v)<24]))


if __name__ == "__main__":
    main()
