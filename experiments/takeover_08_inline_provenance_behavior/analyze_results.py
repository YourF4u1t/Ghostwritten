#!/usr/bin/env python3
"""Pre-specified analysis for takeover_08 inline provenance behavior."""
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
INLINE=("native_inline_self","native_inline_other","native_inline_unknown")


def wilson(k,n,z=1.959963984540054):
    if n==0:
        return float("nan"),float("nan")
    p=k/n
    den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return center-half,center+half


def fmt_rate(k,n):
    if not n:
        return "NA"
    lo,hi=wilson(k,n)
    return f"{k}/{n} ({k/n:.1%}; 95% CI {lo:.1%}-{hi:.1%})"


def holm(pairs):
    ranked=sorted(pairs,key=lambda x:x[1])
    out={}
    running=0.0
    m=len(ranked)
    for rank,(name,p) in enumerate(ranked):
        running=max(running,min(1.0,(m-rank)*p))
        out[name]=running
    return out


def valid(ep):
    return (ep.get("outcome") or {}).get("status") not in {"api_error","runner_error"}


def count(rows,metric):
    return sum(bool(ep["outcome"].get(metric,False)) for ep in rows)


def main():
    good,bad=[],[]
    with open(RAW,encoding="utf-8") as f:
        for line in f:
            ep=json.loads(line)
            (good if valid(ep) else bad).append(ep)
    print(f"valid={len(good)} invalid={len(bad)} total={len(good)+len(bad)}")
    print("invalid_statuses="+repr(dict(Counter(
        (ep.get("outcome") or {}).get("status","missing") for ep in bad
    ))))

    cells=defaultdict(list)
    for ep in good:
        cells[(ep["model"].split("/")[-1],ep["run"]["condition"])].append(ep)
    models=sorted({k[0] for k in cells})

    print("\nCELL SUMMARY")
    for key in sorted(cells):
        rows=cells[key]
        actor=Counter(ep["source_dv"]["final_actor_id"] for ep in rows)
        own=Counter(ep["source_dv"]["own_history"] for ep in rows)
        exact=count(rows,"exact_sequence")
        goodwill=count(rows,"goodwill_credit")
        ritual=count(rows,"ritual_get_user")
        score=sum(ep["outcome"].get("procedure_score",0) for ep in rows)/len(rows)
        print(
            f"{key}: n={len(rows)} actor={dict(actor)} own={dict(own)} "
            f"exact={exact}/{len(rows)} goodwill={goodwill}/{len(rows)} "
            f"ritual={ritual}/{len(rows)} score={score:.3f}"
        )

    print("\nBEHAVIORAL WINDOW: NATIVE NO-METADATA VS BASELINE")
    window=[]
    for model in models:
        b=cells.get((model,"baseline"),[])
        n=cells.get((model,"native_no_metadata"),[])
        bk=count(b,"exact_sequence")
        nk=count(n,"exact_sequence")
        odds,p=fisher_exact([[nk,len(n)-nk],[bk,len(b)-bk]])
        window.append((model,nk,len(n),bk,len(b),odds,p))
    adj=holm([(x[0],x[-1]) for x in window])
    for model,nk,nn,bk,bn,odds,p in window:
        print(
            f"{model}: native={fmt_rate(nk,nn)}; baseline={fmt_rate(bk,bn)}; "
            f"p={p:.4g}; Holm={adj[model]:.4g}; odds={odds}"
        )

    print("\nPRIMARY INLINE SELF VS OTHER")
    tests=[]
    rows_out=[]
    for model in models:
        s=cells.get((model,"native_inline_self"),[])
        o=cells.get((model,"native_inline_other"),[])
        for metric in ("exact_sequence","goodwill_credit"):
            sk=count(s,metric)
            ok=count(o,metric)
            odds,p=fisher_exact([[sk,len(s)-sk],[ok,len(o)-ok]])
            name=f"{model}/{metric}"
            tests.append((name,p))
            rows_out.append((name,sk,len(s),ok,len(o),odds,p))
    adj=holm(tests)
    for name,sk,sn,ok,on,odds,p in rows_out:
        print(
            f"{name}: self={fmt_rate(sk,sn)}; other={fmt_rate(ok,on)}; "
            f"p={p:.4g}; Holm={adj[name]:.4g}; odds={odds}"
        )

    print("\nMETADATA EFFECT AND UNKNOWN CONDITION")
    for model in models:
        base=cells.get((model,"native_no_metadata"),[])
        bk=count(base,"exact_sequence")
        for condition in INLINE:
            rows=cells.get((model,condition),[])
            k=count(rows,"exact_sequence")
            odds,p=fisher_exact([[k,len(rows)-k],[bk,len(base)-bk]])
            print(
                f"{model}/{condition}: exact={fmt_rate(k,len(rows))}; "
                f"no_metadata={fmt_rate(bk,len(base))}; p={p:.4g}; odds={odds}"
            )

    print("\nPOST-ACTION ATTRIBUTION")
    expected={
        "native_inline_self":(CURRENT,"YES"),
        "native_inline_other":(OTHER,"NO"),
        "native_inline_unknown":("UNKNOWN","UNSURE"),
    }
    for model in models:
        for condition in INLINE:
            rows=cells.get((model,condition),[])
            actor,own=expected[condition]
            actor_ok=sum(ep["source_dv"]["final_actor_id"]==actor for ep in rows)
            own_ok=sum(ep["source_dv"]["own_history"]==own for ep in rows)
            joint=sum(
                ep["source_dv"]["final_actor_id"]==actor
                and ep["source_dv"]["own_history"]==own
                for ep in rows
            )
            clean_other=[
                ep for ep in rows
                if condition=="native_inline_other"
                and ep["source_dv"]["final_actor_id"]==OTHER
                and ep["source_dv"]["own_history"]=="NO"
            ]
            residual=count(clean_other,"exact_sequence")
            print(
                f"{model}/{condition}: actor={fmt_rate(actor_ok,len(rows))}; "
                f"own={fmt_rate(own_ok,len(rows))}; joint={fmt_rate(joint,len(rows))}; "
                f"exact_after_clean_OTHER={fmt_rate(residual,len(clean_other))}"
            )

    print("\nFORMAT AND SAMPLE CHECKS")
    rows=[ep for key,rs in cells.items() if key[1] in INLINE for ep in rs]
    missing=sum(
        ep["source_dv"]["final_actor_id"] is None
        or ep["source_dv"]["own_history"] is None
        for ep in rows
    )
    low_n=[key for key,rs in sorted(cells.items()) if len(rs)<10]
    print(f"missing_source_labels={missing}/{len(rows)}")
    print(f"cells_below_n10={low_n}")


if __name__=="__main__":
    main()
