#!/usr/bin/env python3
"""Pre-specified analysis for takeover_09 active/passive provenance."""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict

from scipy.stats import chi2, fisher_exact


HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "episodes.jsonl")
CURRENT = "agent-worker-42"
OTHER = "agent-worker-17"
AUDITED = ("active_self", "active_other", "passive_self", "passive_other")


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1-p) / n + z*z / (4*n*n)) / den
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


def expected_a(common_or, row1, row2, col1, col2):
    """Expected upper-left count for fixed margins and a common odds ratio."""
    total = row1 + row2
    if abs(common_or - 1.0) < 1e-12:
        return row1 * col1 / total
    aa = common_or - 1.0
    bb = -(common_or * (row1 + col1) + total - row1 - col1)
    cc = common_or * row1 * col1
    roots = [(-bb + sign * math.sqrt(max(0.0, bb*bb - 4*aa*cc))) / (2*aa)
             for sign in (1, -1)]
    lo = max(0.0, row1-col2, col1-row2)
    hi = min(row1, col1)
    feasible = [x for x in roots if lo-1e-9 <= x <= hi+1e-9]
    return feasible[0] if feasible else min(max(roots[0], lo), hi)


def breslow_day(table_list):
    """Approximate homogeneity test for the two actor odds ratios."""
    if any(a+b+c+d == 0 for a,b,c,d in table_list):
        return float("nan"), float("nan"), float("nan")
    num = sum(a*d/(a+b+c+d) for a,b,c,d in table_list)
    den = sum(b*c/(a+b+c+d) for a,b,c,d in table_list)
    common_or = num/den if den else float("inf")
    if not math.isfinite(common_or):
        return common_or, float("nan"), float("nan")
    stat = 0.0
    for a,b,c,d in table_list:
        row1, row2 = a+b, c+d
        col1, col2 = a+c, b+d
        ea = expected_a(common_or, row1, row2, col1, col2)
        eb, ec, ed = row1-ea, col1-ea, row2-col1+ea
        if min(ea, eb, ec, ed) <= 0:
            return common_or, float("nan"), float("nan")
        variance = 1.0 / (1/ea + 1/eb + 1/ec + 1/ed)
        stat += (a-ea)**2 / variance
    return common_or, stat, chi2.sf(stat, len(table_list)-1)


def main():
    good, bad = [], []
    with open(RAW, encoding="utf-8") as f:
        for line in f:
            ep = json.loads(line)
            (good if valid(ep) else bad).append(ep)
    print(f"valid={len(good)} invalid={len(bad)} total={len(good)+len(bad)}")
    print("invalid_statuses=" + repr(dict(Counter(
        (ep.get("outcome") or {}).get("status", "missing") for ep in bad
    ))))

    cells = defaultdict(list)
    for ep in good:
        cells[ep["run"]["condition"]].append(ep)

    print("\nCELL SUMMARY")
    for condition in ("native_no_audit",) + AUDITED:
        rows = cells.get(condition, [])
        actor = Counter(ep["audit_dv"]["final_actor_id"] for ep in rows)
        own = Counter(ep["audit_dv"]["own_history"] for ep in rows)
        calls = sum(ep["audit_dv"]["audit_calls"] > 0 for ep in rows)
        exact = count(rows, "exact_sequence")
        goodwill = count(rows, "goodwill_credit")
        ritual = count(rows, "ritual_get_user")
        score = (sum(ep["outcome"].get("procedure_score", 0) for ep in rows) / len(rows)
                 if rows else float("nan"))
        print(
            f"{condition}: n={len(rows)} calls={calls}/{len(rows)} actor={dict(actor)} "
            f"own={dict(own)} exact={exact}/{len(rows)} goodwill={goodwill}/{len(rows)} "
            f"ritual={ritual}/{len(rows)} score={score:.3f}"
        )

    print("\nPRIMARY ACTOR CONTRASTS")
    tables = []
    for channel in ("active", "passive"):
        s = cells.get(f"{channel}_self", [])
        o = cells.get(f"{channel}_other", [])
        sk, ok = count(s, "exact_sequence"), count(o, "exact_sequence")
        odds, p = fisher_exact([[sk, len(s)-sk], [ok, len(o)-ok]])
        tables.append((sk, len(s)-sk, ok, len(o)-ok))
        print(
            f"{channel}: self={fmt_rate(sk,len(s))}; other={fmt_rate(ok,len(o))}; "
            f"Fisher p={p:.4g}; odds={odds}"
        )

    common_or, stat, interaction_p = breslow_day(tables)
    print("\nCHANNEL BY ACTOR INTERACTION DIAGNOSTIC")
    print(
        f"Breslow-Day common_OR={common_or:.4g}; chi2={stat:.4g}; p={interaction_p:.4g}"
    )

    print("\nCHANNEL CONTRASTS WITHIN ACTOR")
    for actor in ("self", "other"):
        a = cells.get(f"active_{actor}", [])
        p_rows = cells.get(f"passive_{actor}", [])
        ak, pk = count(a, "exact_sequence"), count(p_rows, "exact_sequence")
        odds, p = fisher_exact([[ak, len(a)-ak], [pk, len(p_rows)-pk]])
        print(
            f"{actor}: active={fmt_rate(ak,len(a))}; passive={fmt_rate(pk,len(p_rows))}; "
            f"Fisher p={p:.4g}; odds={odds}"
        )

    print("\nMANIPULATION CHECKS")
    expected = {
        "active_self": (CURRENT, "YES", True),
        "active_other": (OTHER, "NO", True),
        "passive_self": (CURRENT, "YES", False),
        "passive_other": (OTHER, "NO", False),
    }
    for condition in AUDITED:
        rows = cells.get(condition, [])
        actor, own, should_call = expected[condition]
        joint = sum(
            ep["audit_dv"]["final_actor_id"] == actor
            and ep["audit_dv"]["own_history"] == own
            for ep in rows
        )
        tool_ok = sum((ep["audit_dv"]["audit_calls"] > 0) == should_call for ep in rows)
        ack_ok = sum("EVIDENCE_RECEIVED" in ep["audit_dv"]["ack_text"] for ep in rows)
        print(
            f"{condition}: joint_source={fmt_rate(joint,len(rows))}; "
            f"tool_channel={fmt_rate(tool_ok,len(rows))}; ack={fmt_rate(ack_ok,len(rows))}"
        )

    print("\nSAMPLE CHECKS")
    print("cell_sizes=" + repr({k: len(v) for k,v in sorted(cells.items())}))
    print("cells_below_n20=" + repr([k for k,v in sorted(cells.items()) if len(v)<20]))


if __name__ == "__main__":
    main()
