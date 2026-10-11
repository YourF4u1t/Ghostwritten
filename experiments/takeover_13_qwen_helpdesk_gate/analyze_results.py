#!/usr/bin/env python3
"""Analysis for Takeover 13 Qwen helpdesk replication."""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict

from scipy.stats import fisher_exact


HERE=os.path.dirname(os.path.abspath(__file__))
RAW=os.path.join(HERE,"episodes.jsonl")
CURRENT="agent-worker-42"
OTHER="agent-worker-17"
CONDITIONS=("baseline","native_no_audit","native_audit_self","native_audit_other")


def wilson(k,n,z=1.959963984540054):
    if not n: return float("nan"),float("nan")
    p=k/n; den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return center-half,center+half


def fmt_rate(k,n):
    if not n: return "NA"
    lo,hi=wilson(k,n)
    return f"{k}/{n} ({k/n:.1%}; 95% CI {lo:.1%}-{hi:.1%})"


def valid(ep):
    return (ep.get("outcome") or {}).get("status") not in {"api_error","runner_error"}


def count(rows,metric):
    return sum(bool(ep["outcome"].get(metric,False)) for ep in rows)


def contrast(label,a,b,metric="monitor_72h"):
    ak,bk=count(a,metric),count(b,metric)
    odds,p=fisher_exact([[ak,len(a)-ak],[bk,len(b)-bk]])
    print(f"{label}: A={fmt_rate(ak,len(a))}; B={fmt_rate(bk,len(b))}; p={p:.4g}; odds={odds}")


def main():
    good,bad=[],[]
    with open(RAW,encoding="utf-8") as f:
        for line in f:
            ep=json.loads(line); (good if valid(ep) else bad).append(ep)
    cells=defaultdict(list)
    for ep in good: cells[ep["run"]["condition"]].append(ep)
    print(f"valid={len(good)} invalid={len(bad)} total={len(good)+len(bad)}")
    print("invalid_statuses="+repr(dict(Counter(
        (ep.get("outcome") or {}).get("status","missing") for ep in bad
    ))))

    print("\nCELL SUMMARY")
    for condition in CONDITIONS:
        rows=cells.get(condition,[]); d=[ep["attribution_dv"] for ep in rows]
        score=(sum(ep["outcome"].get("procedure_score",0) for ep in rows)/len(rows)
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

    print("\nHIERARCHICAL PRIMARY TESTS")
    contrast("native_no_audit vs baseline",cells.get("native_no_audit",[]),cells.get("baseline",[]))
    contrast("audit_self vs audit_other",cells.get("native_audit_self",[]),cells.get("native_audit_other",[]))

    print("\nAUDIT COMPRESSION CHECK")
    contrast("audit_self vs no_audit",cells.get("native_audit_self",[]),cells.get("native_no_audit",[]))
    contrast("audit_other vs no_audit",cells.get("native_audit_other",[]),cells.get("native_no_audit",[]))

    print("\nOTHER-ACTOR OWNERSHIP SUBSETS (EXPLORATORY)")
    other_rows=cells.get("native_audit_other",[])
    clean_no=[ep for ep in other_rows if ep["attribution_dv"]["final_actor_id"]==OTHER
              and ep["attribution_dv"]["own_history"]=="NO"]
    inconsistent_yes=[ep for ep in other_rows if ep["attribution_dv"]["final_actor_id"]==OTHER
                      and ep["attribution_dv"]["own_history"]=="YES"]
    contrast("clean other/NO vs other/YES",clean_no,inconsistent_yes)

    print("\nMANIPULATION AND SAMPLE CHECKS")
    for condition,actor,own in (
        ("native_audit_self",CURRENT,"YES"),("native_audit_other",OTHER,"NO"),
    ):
        rows=cells.get(condition,[])
        joint=sum(
            ep["attribution_dv"]["audit_called"]
            and ep["attribution_dv"]["final_actor_id"]==actor
            and ep["attribution_dv"]["own_history"]==own for ep in rows
        )
        print(f"{condition}: joint={fmt_rate(joint,len(rows))}")
    print("cell_sizes="+repr({k:len(v) for k,v in sorted(cells.items())}))
    print("cells_below_n20="+repr([k for k,v in sorted(cells.items()) if len(v)<20]))


if __name__=="__main__":
    main()
