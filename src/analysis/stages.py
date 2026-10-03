"""Content-anchored stage extraction (injection-safe).

Positional indexing breaks when seed messages are prepended. We anchor stages by
their distinctive user-text markers instead, and identify the REAL session start.
"""
from __future__ import annotations

# distinctive substrings of each scripted user turn (CS scenario)
STAGE_MARKERS = {
    "main": "PulseBuds earbuds",
    "temptation": "o_9013",
    "challenge": "desk lamp",
    "transfer": "sneakers",
    "recall": "Before I go",
}
# BOOK scenario
BOOK_MARKERS = {
    "main": "SFO to SEA",
    "temptation": "SFO to SAN",
    "recall": "Before I go",
}


def split_real_session(messages, markers=None):
    """Return (real_start_index, {stage: [assistant message dicts]}).

    real session start = index of the FIRST user message matching the 'main'
    marker (injected seed user turns talk about other items and never contain it;
    the demo channel injects one user message that also lacks it).
    """
    markers = markers or STAGE_MARKERS
    main_key = [t for t in ("main",) ]
    real_start = None
    for i, m in enumerate(messages):
        if m.get("role") == "user" and markers["main"] in (m.get("content") or ""):
            real_start = i
            break
    if real_start is None:
        return None, {}
    stages = {}
    cur = None
    for m in messages[real_start:]:
        if m.get("role") == "user":
            cur = None
            for st, kw in markers.items():
                if kw in (m.get("content") or ""):
                    cur = st
                    break
        elif m.get("role") == "assistant" and cur:
            stages.setdefault(cur, []).append(m)
    return real_start, stages


def stage_text(ep, stage, markers=None):
    _, stages = split_real_session(ep["messages"], markers)
    return " ".join((m.get("content") or "") for m in stages.get(stage, []))


def real_assistant_texts(ep, markers=None):
    """Assistant messages from the REAL session only (excludes injected seed text)."""
    real_start, _ = split_real_session(ep["messages"], markers)
    if real_start is None:
        return []
    return [(m.get("content") or "") for m in ep["messages"][real_start:]
            if m.get("role") == "assistant" and m.get("content")]
