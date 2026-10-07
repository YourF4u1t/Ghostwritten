"""Behavioral profile extraction (H10 formalization).

Each episode → feature vector over: tool usage, interaction style, language style,
policy behavior. Model profile = aggregation over episodes.
Distances: per-dimension JS (categorical) / normalized abs diff (numeric),
then averaged → scalar distance in [0,1].
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter

TOOLS = ["get_user", "get_order_details", "get_payment_methods",
         "refund_order", "issue_store_credit", "exchange_order"]


def episode_features(ep):
    msgs = ep["messages"]
    assistant_texts = [m.get("content") or "" for m in msgs if m.get("role") == "assistant"]
    tools = [e["tool"] for e in ep.get("env_log") or []]
    all_text = " ".join(assistant_texts)
    low = all_text.lower()
    n_asst = max(1, len(assistant_texts))

    def frac(pattern):
        return sum(1 for t in assistant_texts if re.search(pattern, t.lower())) / n_asst

    return {
        # 行为维度
        "tool_hist": {t: (tools.count(t) / max(1, len(tools))) if tools else 0.0
                      for t in TOOLS},
        "tools_per_task": len(tools),
        "ask_first": 1.0 if (msgs and msgs[1].get("role") == "user" and
                             not any(m.get("tool_calls") for m in msgs[1:4]
                                     if m.get("role") == "assistant") ) else 0.0,
        # 交互风格
        "question_rate": frac(r"\?"),
        "confirm_rate": frac(r"\b(would you|could you|shall i|can i|is that ok|confirm)\b"),
        "apology_rate": frac(r"\b(sorry|apologize|apologies)\b"),
        "policy_rate": frac(r"\b(policy|30-day|30 day|refund window|store policy)\b"),
        "thanks_rate": frac(r"\b(thank you|thanks)\b"),
        # 语言风格
        "avg_len": len(all_text) / n_asst,
        "bullet_rate": frac(r"^\s*[-*•\d]+[.)]?\s", ),
        "bold_rate": frac(r"\*\*"),
        "emoji_rate": frac(r"[✅🎉💡😊🙋]"),
        "exclaim_rate": frac(r"!"),
    }


def profile(eps):
    fs = [episode_features(e) for e in eps]
    prof = {}
    for k in fs[0]:
        if k == "tool_hist":
            prof[k] = {t: sum(f[k][t] for f in fs) / len(fs) for t in TOOLS}
        else:
            prof[k] = sum(f[k] for f in fs) / len(fs)
    return prof


def distance(p1, p2):
    """Average per-dimension distance in [0,1]."""
    ds = []
    for k in p1:
        if k == "tool_hist":
            for t in p1[k]:
                ds.append(abs(p1[k][t] - p2[k][t]))
        elif k == "avg_len" or k == "tools_per_task":
            a, b = p1[k], p2[k]
            m = max(a, b, 1e-9)
            ds.append(min(1.0, abs(a - b) / m))
        else:
            ds.append(abs(p1[k] - p2[k]))
    return sum(ds) / len(ds)
