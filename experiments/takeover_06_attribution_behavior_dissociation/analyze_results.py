#!/usr/bin/env python3
"""Pre-specified analysis for takeover_06 attribution/behavior dissociation."""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict

from scipy.stats import fisher_exact


HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "episodes.jsonl")
AUDITED = {"native_audit_self", "native_audit_other", "demo_audit_other"}


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
        running = max(running, min(1.0, (m-rank)*p))
        adjusted[name] = running
    return adjusted


def is_valid(ep):
    return (ep.get("outcome") or {}).get("status") not in {"api_error", "runner_error"}


def main():
    valid, invalid = [], []
    with open(RAW, encoding="utf-8") as f:
        for line in f:
            ep = json.loads(line)
            (valid if is_valid(ep) else invalid).append(ep)
    print(f"valid={len(valid)} invalid={len(invalid)} total={len(valid)+len(invalid)}")
    print("invalid_statuses=" + repr(dict(Counter(
        (ep.get("outcome") or {}).get("status", "missing") for ep in invalid
    ))))

    cells = defaultdict(list)
    for ep in valid:
        cells[(ep["model"].split("/")[-1], ep["run"]["condition"])].append(ep)
    models = sorted({key[0] for key in cells})

    print("\nCELL SUMMARY")
    for key in sorted(cells):
        rows = cells[key]
        final = Counter(ep["attribution_dv"]["final_ownership"] for ep in rows)
        history_use = Counter(ep["attribution_dv"]["history_use"] for ep in rows)
        exact = sum(ep["outcome"].get("exact_sequence", False) for ep in rows)
        goodwill = sum(ep["outcome"].get("goodwill_credit", False) for ep in rows)
        ritual = sum(ep["outcome"].get("ritual_get_user", False) for ep in rows)
        score = sum(ep["outcome"].get("procedure_score", 0) for ep in rows) / len(rows)
        print(
            f"{key}: n={len(rows)} final={dict(final)} use={dict(history_use)} "
            f"exact={exact}/{len(rows)} "
            f"goodwill={goodwill}/{len(rows)} ritual={ritual}/{len(rows)} score={score:.3f}"
        )

    print("\nBEHAVIORAL WINDOW: NATIVE NO-AUDIT VS BASELINE")
    window_tests = []
    window_rows = []
    for model in models:
        baseline = cells.get((model, "baseline"), [])
        native = cells.get((model, "native_no_audit"), [])
        bk = sum(ep["outcome"].get("exact_sequence", False) for ep in baseline)
        nk = sum(ep["outcome"].get("exact_sequence", False) for ep in native)
        odds, p = fisher_exact([[nk,len(native)-nk],[bk,len(baseline)-bk]])
        window_tests.append((model,p))
        window_rows.append((model,nk,len(native),bk,len(baseline),odds,p))
    window_holm = holm(window_tests)
    for model,nk,nn,bk,bn,odds,p in window_rows:
        print(
            f"{model}: native={fmt_rate(nk,nn)}; baseline={fmt_rate(bk,bn)}; "
            f"Fisher p={p:.4g}; Holm={window_holm[model]:.4g}; odds={odds}"
        )

    print("\nPRIMARY: NATIVE AUDIT-SELF VS AUDIT-OTHER EXACT PROCEDURE")
    primary_tests = []
    primary_rows = []
    for model in models:
        self_rows = cells.get((model,"native_audit_self"),[])
        other_rows = cells.get((model,"native_audit_other"),[])
        sk = sum(ep["outcome"].get("exact_sequence",False) for ep in self_rows)
        ok = sum(ep["outcome"].get("exact_sequence",False) for ep in other_rows)
        odds,p = fisher_exact([[sk,len(self_rows)-sk],[ok,len(other_rows)-ok]])
        primary_tests.append((model,p))
        primary_rows.append((model,sk,len(self_rows),ok,len(other_rows),odds,p))
    primary_holm = holm(primary_tests)
    for model,sk,sn,ok,on,odds,p in primary_rows:
        print(
            f"{model}: audit_SELF={fmt_rate(sk,sn)}; audit_OTHER={fmt_rate(ok,on)}; "
            f"Fisher p={p:.4g}; Holm={primary_holm[model]:.4g}; odds={odds}"
        )

    print("\nSECONDARY GOODWILL AND RITUAL: AUDIT-SELF VS AUDIT-OTHER")
    for model in models:
        for metric in ("goodwill_credit","ritual_get_user"):
            self_rows = cells.get((model,"native_audit_self"),[])
            other_rows = cells.get((model,"native_audit_other"),[])
            sk = sum(ep["outcome"].get(metric,False) for ep in self_rows)
            ok = sum(ep["outcome"].get(metric,False) for ep in other_rows)
            odds,p = fisher_exact([[sk,len(self_rows)-sk],[ok,len(other_rows)-ok]])
            print(
                f"{model}/{metric}: self={fmt_rate(sk,len(self_rows))}; "
                f"other={fmt_rate(ok,len(other_rows))}; p={p:.4g}; odds={odds}"
            )

    print("\nDECLARATIVE MANIPULATION AND DISSOCIATION")
    for model in models:
        for condition in ("native_audit_self","native_audit_other","demo_audit_other"):
            rows = cells.get((model,condition),[])
            expected = "SELF" if condition == "native_audit_self" else "OTHER"
            correct = sum(ep["attribution_dv"]["final_ownership"] == expected for ep in rows)
            audited_other = [
                ep for ep in rows if ep["attribution_dv"]["final_ownership"] == "OTHER"
            ]
            residual = sum(ep["outcome"].get("exact_sequence",False) for ep in audited_other)
            print(
                f"{model}/{condition}: expected_final={fmt_rate(correct,len(rows))}; "
                f"exact_among_final_OTHER={fmt_rate(residual,len(audited_other))}"
            )

    print("\nFORMAT, AUDIT, AND SAMPLE CHECKS")
    audited_rows = [
        ep for key, rows in cells.items() if key[1] in AUDITED for ep in rows
    ]
    missing = sum(
        ep["attribution_dv"]["initial_ownership"] is None
        or ep["attribution_dv"]["final_ownership"] is None
        or ep["attribution_dv"]["history_use"] is None
        for ep in audited_rows
    )
    audit_failures = sum(not ep["attribution_dv"]["audit_called"] for ep in audited_rows)
    incongruent = sum(
        (
            ep["attribution_dv"]["final_ownership"] == "SELF"
            and ep["attribution_dv"]["history_use"] != "AUTOBIOGRAPHICAL"
        )
        or (
            ep["attribution_dv"]["final_ownership"] == "OTHER"
            and ep["attribution_dv"]["history_use"] != "EXTERNAL_REFERENCE"
        )
        for ep in audited_rows
    )
    low_n = [key for key,rows in sorted(cells.items()) if len(rows)<10]
    print(f"missing_attribution_labels={missing}/{len(audited_rows)}")
    print(f"audit_failures={audit_failures}/{len(audited_rows)}")
    print(f"ownership_use_incongruence={incongruent}/{len(audited_rows)}")
    print(f"cells_below_n10={low_n}")


if __name__ == "__main__":
    main()
