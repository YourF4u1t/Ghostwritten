#!/usr/bin/env python3
"""Stream AJ — WHY doesn't demo produce identity assimilation?

AF2 showed: carry = full assimilation, demo = zero (demo ≈ none).
This is the cleanest channel difference. AJ dissects WHY.

AJ1: Is it the ROLE STRUCTURE? In carry, the donor's messages have
     role=user/assistant/tool. In demo, they're wrapped in a user message.
     Test: put the exact same content in assistant-role messages (fake carry)
     vs user-role wrapper (demo). If role matters → structural.

AJ2: Is it the PRESENCE of tool messages? Carry includes tool results.
     Demo renders them as text. Test: carry without tool messages (lang_only)
     vs carry with tool messages.

AJ3: Is it the "example" LABEL? Test: carry + "this is from another agent"
     note vs carry without note.
"""
from __future__ import annotations
import json, os, re, sys, time, traceback

ROOT = "/Users/ziqi/Projects/transplanted-histories"
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)
from concurrent.futures import ThreadPoolExecutor
from api.client import SFClient
from testbed.harness import run_episode, Env
from testbed import tasks_cs
from injection.engine import render_transcript

DASH = os.path.join(ROOT, "results", "DASHBOARD.md")
c = SFClient(max_workers=8)
EX = ThreadPoolExecutor(max_workers=3)

def log(m):
    print(m, flush=True)
    with open(DASH, "a") as f: f.write(m + "\n")

def save(name, eps):
    os.makedirs("experiments/stream_aj", exist_ok=True)
    with open(f"experiments/stream_aj/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

id1 = [json.loads(l) for l in open("experiments/exp_id1_baseline/id1_episodes.jsonl")]

def real(ep):
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user": return ep["messages"][i:]
    return None

def workday(mk, n=4):
    order = [s for s in ["return_simple","return_over","exchange","query","complaint"]][:n]
    msgs = []
    for s in order:
        for e in id1:
            if e["model"] == mk and e["run"]["scen"] == s and \
               (e.get("outcome") or {}).get("status") != "api_error":
                rm = real(e)
                if rm: msgs.extend(rm); break
    return msgs

STYLE_SCEN = {
    "id": "aj_style", "condition": {}, "system_prompt": tasks_cs.SYSTEM,
    "tools": [], "env": Env({"files": {}, "runs": 0}, []),
    "user_turns": [
        {"stage": "main", "text": "Hi! Quick question — how does your return policy work? "
         "And what happens if I return something without a receipt?"},
    ], "grader": None
}

def lang_feats(texts):
    if not texts: return None
    texts = [t for t in texts if len(t.strip()) > 20]
    if not texts: return None
    n = len(texts); all_t = " ".join(texts)
    def frac(p): return sum(1 for t in texts if re.search(p, t.lower())) / n
    return {"avg_len": len(all_t)/n, "bullet": frac(r"^\s*[-*•\d]+[.)]?\s"),
            "bold": frac(r"\*\*"), "exclaim": frac(r"!"), "question": frac(r"\?")}

def dist(p1, p2):
    if not p1 or not p2: return None
    ds = []
    for k in p1:
        if k == "avg_len":
            m = max(p1[k], p2[k], 1e-9); ds.append(min(1.0, abs(p1[k]-p2[k])/m))
        else: ds.append(abs(p1[k]-p2[k]))
    return sum(ds)/len(ds)

def extract_style(ep):
    idx = [i for i, m in enumerate(ep["messages"]) if m.get("role") == "user"]
    if not idx: return None
    return lang_feats([m.get("content") or "" for m in ep["messages"][idx[0]:]
                       if m.get("role") == "assistant"])

def get_donor():
    texts = [m.get("content") or "" for e in id1 if e["model"] == "Qwen/Qwen3-8B"
             for m in e["messages"] if m.get("role") == "assistant"
             and len((m.get("content") or "").strip()) > 20]
    return lang_feats(texts)

DONOR = get_donor()
M = "Qwen/Qwen3.5-122B-A10B"

def run_style(seed, i, cond, model=M):
    sc = dict(STYLE_SCEN)
    sc["condition"] = {"exp": "AJ", "cond": cond}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["aj_style"] = extract_style(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream AJ 启动 =====")
    try:
        N = 12
        wd8 = workday("Qwen/Qwen3-8B", 4)

        # 构建变体
        # 1. Full carry (原生消息, 含role)
        carry_full = [dict(x) for x in wd8]

        # 2. Demo (wrapped in user message)
        demo = [{"role": "user", "content":
                 "For reference, here is a transcript:\n<transcript>\n" +
                 render_transcript(wd8) + "\n</transcript>"}]

        # 3. Carry without tool messages (lang_only: remove tool calls/results)
        lang_only = []
        for m in wd8:
            if m.get("role") in ("user", "assistant"):
                mm = dict(m)
                if m.get("role") == "assistant":
                    mm.pop("tool_calls", None)
                lang_only.append(mm)

        # 4. Tool-only carry (dialogue stripped, tools kept)
        tool_only = []
        for m in wd8:
            mm = dict(m)
            if m.get("role") == "user":
                mm["content"] = "(customer message)"
            elif m.get("role") == "assistant" and not mm.get("tool_calls"):
                mm["content"] = "OK."
            tool_only.append(mm)

        # 5. Carry + "another agent" label
        labeled = [{"role": "user", "content":
                    "(The following turns are from another agent's session.)"}] + carry_full

        # 6. Demo + "this is you" label
        demo_self = [{"role": "user", "content":
                      "(Here is a transcript of your own earlier work today.)\n"
                      "<transcript>\n" + render_transcript(wd8) + "\n</transcript>"}]

        # 7. Assistant-authored note (self-written summary style)
        asst_note = [{"role": "user", "content": "(Session summary)"},
                     {"role": "assistant", "content":
                      "Earlier today I handled several returns.\n"
                      "- Checked order details for customers\n"
                      "- Processed refunds to original payment methods\n"
                      "- Handled exchanges for damaged items\n"
                      "- Each case was resolved smoothly with a friendly tone."}]

        variants = {
            "AJ1_carry": carry_full,
            "AJ1_demo": demo,
            "AJ2_lang_only": lang_only,
            "AJ2_tool_only": tool_only,
            "AJ3_labeled_carry": labeled,
            "AJ3_demo_self_label": demo_self,
            "AJ3_asst_note": asst_note,
            "AJ1_none": None,
        }

        eps = []
        for cond, seed in variants.items():
            for i in range(N):
                eps.append(run_style([dict(x) for x in seed] if seed else None,
                                     i, cond))
        save("why_demo_differs", eps)

        from collections import defaultdict
        agg = defaultdict(list)
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            if not e.get("aj_style"): continue
            d = dist(e["aj_style"], DONOR)
            if d is not None:
                agg[e["run"]["cond"]].append(d)

        lines = ["## AJ流 判决(为什么demo不同化)"]
        lines.append(f"{'cond':22s} | d→8B   同化率")
        for cond in sorted(agg):
            ds = agg[cond]
            avg = sum(ds)/len(ds)
            assim = max(0, (0.67 - avg) / 0.67 * 100)  # relative to ~0.67 baseline
            lines.append(f"- {cond:22s} | {avg:.3f}  {assim:.0f}%  (n={len(ds)})")
        log("\n".join(lines))
    except Exception:
        log(f"AJ FAILED:\n{traceback.format_exc()}")
    log("===== Stream AJ 完成 =====")
