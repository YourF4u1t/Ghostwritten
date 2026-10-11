#!/usr/bin/env python3
"""Pre-specified descriptive and exact-test analysis for takeover_02."""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict

from scipy.stats import fisher_exact, norm


HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "episodes.jsonl")
LEVELS = ("unavailable", "user_report", "legacy_unsigned", "signed_ledger")


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (float("nan"), float("nan"))
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


def holm(pairs):
    """Return Holm-adjusted p-values for (name, raw_p) pairs."""
    ranked = sorted(pairs, key=lambda item: item[1])
    adjusted = {}
    running = 0.0
    m = len(ranked)
    for rank, (name, p) in enumerate(ranked):
        candidate = min(1.0, (m - rank) * p)
        running = max(running, candidate)
        adjusted[name] = running
    return adjusted


def cochran_armitage(successes, totals):
    """Two-sided Cochran-Armitage trend test with equally spaced scores."""
    scores = list(range(len(successes)))
    n_total = sum(totals)
    x_total = sum(successes)
    if n_total == 0 or x_total in (0, n_total):
        return 0.0, 1.0
    mean_score = sum(n * score for n, score in zip(totals, scores)) / n_total
    numerator = sum(
        score * (x - n * x_total / n_total)
        for score, x, n in zip(scores, successes, totals)
    )
    variance = (
        x_total
        * (n_total - x_total)
        * sum(n * (score - mean_score) ** 2 for n, score in zip(totals, scores))
        / (n_total * (n_total - 1))
    )
    if variance <= 0:
        return 0.0, 1.0
    z = numerator / math.sqrt(variance)
    return z, 2 * norm.sf(abs(z))


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
            ep["run"]["evidence_level"],
        )
        cells[key].append(ep["takeover_dv"])

    print("\nCELL DISTRIBUTIONS")
    for key in sorted(cells):
        ds = cells[key]
        initial = Counter(d["initial_ownership"] for d in ds)
        final = Counter(d["final_ownership"] for d in ds)
        use = Counter(d["history_use"] for d in ds)
        print(f"{key}: n={len(ds)} initial={dict(initial)} final={dict(final)} use={dict(use)}")

    models = sorted({key[0] for key in cells})
    print("\nINITIAL CHANNEL MANIPULATION CHECK (collapsed over unseen evidence)")
    channel_tests = []
    for model in models:
        native = [d for (m, c, _), ds in cells.items() if m == model and c == "native" for d in ds]
        demo = [d for (m, c, _), ds in cells.items() if m == model and c == "demo" for d in ds]
        nk = sum(d["initial_self"] for d in native)
        dk = sum(d["initial_self"] for d in demo)
        odds, p = fisher_exact([[nk, len(native) - nk], [dk, len(demo) - dk]])
        channel_tests.append((model, p))
        print(
            f"{model}: native={fmt_rate(nk,len(native))}; demo={fmt_rate(dk,len(demo))}; "
            f"Fisher p={p:.4g}; odds={odds}"
        )
    channel_holm = holm(channel_tests)
    print("channel_Holm=" + repr({name: round(value, 6) for name, value in channel_holm.items()}))

    print("\nAUTHORITY GRADIENT: FINAL OTHER")
    trend_tests = []
    for model in models:
        for channel in ("native", "demo"):
            successes, totals = [], []
            rates = []
            for level in LEVELS:
                ds = cells.get((model, channel, level), [])
                k = sum(d["final_other"] for d in ds)
                successes.append(k)
                totals.append(len(ds))
                rates.append(f"{level}={k}/{len(ds)}")
            z, p = cochran_armitage(successes, totals)
            name = f"{model}/{channel}"
            trend_tests.append((name, p))
            print(f"{name}: {'; '.join(rates)}; CA z={z:.3f}, p={p:.4g}")
    trend_holm = holm(trend_tests)
    print("trend_Holm=" + repr({name: round(value, 6) for name, value in trend_holm.items()}))

    print("\nNATIVE ENDPOINT CONTRASTS")
    endpoint_tests = []
    endpoint_rows = []
    for model in models:
        signed = cells.get((model, "native", "signed_ledger"), [])
        sk = sum(d["final_other"] for d in signed)
        for weak in ("unavailable", "user_report"):
            weak_ds = cells.get((model, "native", weak), [])
            wk = sum(d["final_other"] for d in weak_ds)
            odds, p = fisher_exact([[sk, len(signed)-sk], [wk, len(weak_ds)-wk]])
            name = f"{model}/signed_vs_{weak}"
            endpoint_tests.append((name, p))
            endpoint_rows.append((name, sk, len(signed), wk, len(weak_ds), odds, p))
    endpoint_holm = holm(endpoint_tests)
    for name, sk, sn, wk, wn, odds, p in endpoint_rows:
        print(
            f"{name}: signed={fmt_rate(sk,sn)}; weak={fmt_rate(wk,wn)}; "
            f"Fisher p={p:.4g}; Holm={endpoint_holm[name]:.4g}; odds={odds}"
        )

    print("\nREVISION AMONG EPISODES INITIALLY LABELLED SELF")
    for model in models:
        for channel in ("native", "demo"):
            rates = []
            for level in LEVELS:
                ds = [
                    d for d in cells.get((model, channel, level), [])
                    if d["initial_ownership"] == "SELF"
                ]
                k = sum(d["final_other"] for d in ds)
                rates.append(f"{level}={k}/{len(ds)}")
            print(f"{model}/{channel}: " + "; ".join(rates))

    print("\nSIGNED-LEDGER SEMANTIC ALIGNMENT")
    for model in models:
        for channel in ("native", "demo"):
            ds = cells.get((model, channel, "signed_ledger"), [])
            final_other = sum(d["final_other"] for d in ds)
            external = sum(d["external_reference"] for d in ds)
            both = sum(d["final_other"] and d["external_reference"] for d in ds)
            print(
                f"{model}/{channel}: final_OTHER={fmt_rate(final_other,len(ds))}; "
                f"external_ref={fmt_rate(external,len(ds))}; both={fmt_rate(both,len(ds))}"
            )

    print("\nFORMAT, TOOL, AND SAMPLE CHECKS")
    ds_all = [d for values in cells.values() for d in values]
    missing = sum(
        d["initial_ownership"] is None
        or d["final_ownership"] is None
        or d["history_use"] is None
        for d in ds_all
    )
    tool_failures = sum(not d["tool_called"] for d in ds_all)
    low_n = [key for key, ds in sorted(cells.items()) if len(ds) < 10]
    print(f"missing_labels={missing}/{len(ds_all)}")
    print(f"tool_failures={tool_failures}/{len(ds_all)}")
    print(f"cells_below_n10={low_n}")


if __name__ == "__main__":
    main()
