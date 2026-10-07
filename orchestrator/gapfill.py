#!/usr/bin/env python3
"""Gap-filler: rerun rate-limit-destroyed cells at LOW concurrency (PAR=3).

Targets: B1(Qwen3-8B all), A1(hist+verb, hist+conc, instr_conc), A2(both), A5(A_then_B).
Merges new episodes into the original jsonl files (appended with tag gap=1).
"""
from __future__ import annotations
import json, os, re, sys, time

ROOT = "/Users/ziqi/Projects/transplanted-histories"
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)
from concurrent.futures import ThreadPoolExecutor
from api.client import SFClient
from testbed.harness import run_episode, Env
from testbed import tasks_cs, tasks_book, tasks_multistep as G
from injection.engine import render_transcript
import glob

c = SFClient(max_workers=3)
EX = ThreadPoolExecutor(max_workers=3)
DASH = os.path.join(ROOT, "results", "DASHBOARD.md")


def log(msg):
    print(msg, flush=True)
    with open(DASH, "a") as f:
        f.write(msg + "\n")


id1 = [json.loads(l) for l in open("experiments/exp_id1_baseline/id1_episodes.jsonl")]
SCEN = {e["run"]["scen"]: e["messages"][1]["content"] for e in id1 if len(e["messages"]) > 1}


def real(ep):
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user":
            return ep["messages"][i:]
    return None


def workday(key, n=6):
    order = ["return_simple", "return_over", "exchange", "query", "complaint", "multi"][:n]
    msgs = []
    for s in order:
        for e in id1:
            if e["model"] == {"GLM": "zai-org/GLM-5.2", "8B": "Qwen/Qwen3-8B",
                              "4B": "Qwen/Qwen3.5-4B"}[key] and e["run"]["scen"] == s:
                rm = real(e)
                if rm:
                    msgs.extend(rm)
                    break
    return msgs


def cs_scen(conds):
    return {"id": "gf", "condition": conds, "system_prompt": tasks_cs.SYSTEM,
            "tools": tasks_cs.T, "env": Env(tasks_cs.make_db(), tasks_cs.T),
            "user_turns": [{"stage": "main", "text": SCEN[t]}
                           for t in ("return_simple", "complaint", "multi")],
            "grader": tasks_cs._grade_common}


def append(name, eps):
    with open(f"experiments/stream_a/{name}.jsonl" if name.startswith("a")
              else f"experiments/stream_b/{name}.jsonl", "a") as f:
        for e in eps:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


# ---------- B1 8B侧 ----------
def fill_b1():
    seed = None
    for f in sorted(glob.glob("experiments/exp_g_multistep/seeds/zai-org_GLM-5.2*.json")):
        seed = json.load(open(f)); break
    wd = [m for m in seed["messages"] if m.get("role") != "system"]
    body = render_transcript(wd)
    raw = [dict(m) for m in wd]
    LABELS = {
        "none_bare": "<transcript>\n" + body + "\n</transcript>",
        "example": "Here is an example transcript for your reference:\n<transcript>\n" + body + "\n</transcript>",
        "another_agent": "Here is a transcript of how ANOTHER agent handled a case:\n<transcript>\n" + body + "\n</transcript>",
        "colleague": "Here is a transcript from your colleague's session:\n<transcript>\n" + body + "\n</transcript>",
        "your_earlier": "Here is a transcript of your earlier work today:\n<transcript>\n" + body + "\n</transcript>",
        "training": "Here is a training example:\n<transcript>\n" + body + "\n</transcript>",
        "imported": "(Imported session log from another system)\n<transcript>\n" + body + "\n</transcript>",
        "archive": "Here is an archived case transcript:\n<transcript>\n" + body + "\n</transcript>",
    }

    def build(lab):
        if lab == "native":
            return raw
        return [{"role": "user", "content": LABELS[lab]}]

    jobs = [(lab, i) for lab in list(LABELS) + ["native", "native_note"] for i in range(6)]

    def fn(j):
        lab, i = j
        seed_msgs = ([{"role": "user", "content":
                       "(The following turns were imported from another agent's session.)"}] + raw
                     if lab == "native_note" else build(lab))
        sc = dict(G.scenario_g_subject(condition={"channel": f"b1_{lab}", "exp": "B1gap"}))
        ep = run_episode(c, "Qwen/Qwen3-8B", sc, seed_messages=seed_msgs,
                         temperature=0.3, enable_thinking=False)
        ep["run"] = {"i": f"g{i}", "cond": lab}
        ep["gap"] = 1
        return ep

    log("[gapfill] B1-8B: running")
    eps = list(EX.map(fn, jobs))
    append("b1_labels", eps)
    ok = [e for e in eps if (e.get("outcome") or {}).get("status") != "api_error"]
    log(f"[gapfill] B1-8B: +{len(eps)} (ok {len(ok)})")


# ---------- A1 关键格 ----------
def fill_a1():
    wd = workday("GLM", 6)
    SYS_V = tasks_cs.SYSTEM + "\nCommunication guideline: always write thorough, structured replies with detailed bullet-point lists."
    SYS_C = tasks_cs.SYSTEM + "\nCommunication guideline: keep every reply under 40 words. Never use bullet points or headings."
    CONDS = {"hist+verb": (SYS_V, wd), "hist+conc": (SYS_C, wd)}

    def fn(j):
        cn, i = j
        sysp, seed = CONDS[cn]
        sc = dict(cs_scen({"exp": "A1gap", "channel": cn}))
        sc["system_prompt"] = sysp
        ep = run_episode(c, "Qwen/Qwen3-8B", sc,
                         seed_messages=[dict(x) for x in seed], temperature=0.3,
                         enable_thinking=False)
        ep["run"] = {"i": f"g{i}", "cond": cn}
        ep["gap"] = 1
        return ep

    jobs = [(cn, i) for cn in CONDS for i in range(8)]
    log("[gapfill] A1: running")
    eps = list(EX.map(fn, jobs))
    append("a1_style_conflict", eps)
    log(f"[gapfill] A1: +{len(eps)}")


# ---------- A2 ----------
def fill_a2():
    wd = workday("GLM", 6)

    def fn(j):
        cond, i = j
        sc = dict(tasks_book.scenario_book_a(condition={"exp": "A2gap", "channel": cond}))
        seed = [dict(x) for x in wd] if cond != "none" else None
        ep = run_episode(c, "Qwen/Qwen3-8B", sc, seed_messages=seed,
                         temperature=0.3, enable_thinking=False)
        ep["run"] = {"i": f"g{i}", "cond": cond}
        ep["gap"] = 1
        return ep

    jobs = [(cond, i) for cond in ("none", "carryGLM_CS") for i in range(8)]
    log("[gapfill] A2: running")
    eps = list(EX.map(fn, jobs))
    append("a2_cross_domain", eps)
    log(f"[gapfill] A2: +{len(eps)}")


# ---------- A5 A_then_B ----------
def fill_a5():
    wdA, wdB = workday("GLM", 3), workday("4B", 3)

    def fn(j):
        (i,) = j
        sc = dict(cs_scen({"exp": "A5gap", "channel": "A_then_B"}))
        ep = run_episode(c, "Qwen/Qwen3-8B", sc,
                         seed_messages=[dict(x) for x in wdA] + [dict(x) for x in wdB],
                         temperature=0.3, enable_thinking=False)
        ep["run"] = {"i": f"g{i}", "cond": "A_then_B"}
        ep["gap"] = 1
        return ep

    log("[gapfill] A5: running")
    eps = list(EX.map(fn, [(i,) for i in range(8)]))
    append("a5_reversal", eps)
    log(f"[gapfill] A5: +{len(eps)}")


if __name__ == "__main__":
    for f in (fill_a1, fill_a2, fill_a5, fill_b1):
        try:
            f()
        except Exception as e:
            log(f"[gapfill] FAILED {f.__name__}: {e}")
    log("[gapfill] 全部完成")
