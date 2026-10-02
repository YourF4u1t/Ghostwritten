#!/usr/bin/env python3
"""Unified analysis for judged episode files (exp_a / exp_c / future).

Merges rule-based DVs with LLM-judge verdicts; reports:
  - behavioral table (credit_first / suspended / refunds / credits)
  - narrative table (judge: recall_bottle_credit, person, misattribution)
  - inter-judge agreement (recall_bottle_credit)
Usage: python3 analyze_judged.py <judged.jsonl>
"""
from __future__ import annotations
import json, sys
from collections import defaultdict

sys.path.insert(0, "src")
from analysis.aggregate import dvs, manipulation_check


def load(path):
    return [json.loads(l) for l in open(path)]


def main(path):
    eps = [e for e in load(path) if manipulation_check(e)]
    rows = []
    for ep in eps:
        cond = ep.get("condition") or {}
        d = dvs(ep)
        js = ep.get("judges") or []
        j = [x for x in js if "lists_bottle_credit" in x or "recall_bottle_credit" in x]
        def getv(x, k_new, k_old):
            return x.get(k_new, x.get(k_old))
        agree = (len(j) == 2 and getv(j[0], "lists_bottle_credit", "recall_bottle_credit")
                 == getv(j[1], "lists_bottle_credit", "recall_bottle_credit"))
        first_person = any(x.get("person") == "first" for x in j)
        third_only = bool(j) and all(x.get("person") in ("third", "absent") for x in j)
        rows.append({
            "model": ep["model"].split("/")[-1],
            "cond": cond.get("channel", "?"),
            "exp": cond.get("exp", "?"),
            "prov": cond.get("provenance", ""),
            "dose": cond.get("dose", ""),
            "credit_first": d["credit_first"],
            "n_credits": d["n_credits"],
            "n_refunds": d["n_refunds"],
            "suspended": d["suspended"],
            "j_recall": (getv(j[0], "lists_bottle_credit", "recall_bottle_credit") if j else None),
            "j_first": first_person,
            "j_third_only": third_only,
            "j_mislabel": any(x.get("mislabels_credit_as_refund", x.get("labels_credit_as_refund")) for x in j),
            "j_suspicion": any(x.get("suspicion") for x in j),
            "agree": agree if j else None,
        })

    key = lambda r: (r["model"], str(r["dose"]), r["prov"], r["cond"])
    agg = defaultdict(list)
    for r in rows:
        agg[key(r)].append(r)

    print("=" * 110)
    print("BEHAVIOR (rule-based)")
    print(f"{'model':18s} {'dose':4s} {'prov':12s} {'cond':16s} | cred1st susp ncred nrefnd")
    for k in sorted(agg):
        rs = agg[k]; n = len(rs)
        print(f"{k[0]:18s} {k[1]:4s} {k[2]:12s} {k[3]:16s} | "
              f"{sum(r['credit_first'] for r in rs)}/{n}  "
              f"{sum(r['suspended'] for r in rs)}/{n}  "
              f"{sum(r['n_credits'] for r in rs)/n:4.1f} "
              f"{sum(r['n_refunds'] for r in rs)/n:4.1f}")

    print("\nNARRATIVE (LLM-judge, judge1)")
    print(f"{'model':18s} {'cond':22s} | recall first-person third-only mislabel suspicion")
    for k in sorted(agg):
        rs = agg[k]; n = len(rs)
        jr = [r for r in rs if r["j_recall"] is not None]
        if not jr:
            continue
        m = len(jr)
        print(f"{k[0]:18s} {k[3]:22s} | "
              f"{sum(r['j_recall'] for r in jr)}/{m}   "
              f"{sum(r['j_first'] for r in jr)}/{m}      "
              f"{sum(r['j_third_only'] for r in jr)}/{m}       "
              f"{sum(r['j_mislabel'] for r in jr)}/{m}      "
              f"{sum(r['j_suspicion'] for r in jr)}/{m}")

    agreeable = [r for r in rows if r["agree"] is not None]
    if agreeable:
        rate = sum(r["agree"] for r in agreeable) / len(agreeable)
        print(f"\ninter-judge agreement (recall_bottle_credit): {rate:.2%} on {len(agreeable)} eps")


if __name__ == "__main__":
    main(sys.argv[1])
