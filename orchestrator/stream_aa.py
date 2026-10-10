#!/usr/bin/env python3
"""Stream AA — Mechanism of 8B's generalized foreign-history fragility.

Z showed 8B stops retrying after ANY foreign history (same/diff tool/domain).
AA dissects WHY:

AA1: What if the foreign history has NO tool calls at all? (pure conversation)
     If still suppresses → it's about "having foreign context", not tool success
AA2: What if the history is labeled as a completely different session?
     (e.g., "(From a different agent's session on a different platform)")
AA3: What if we replace the 503 with a DIFFERENT failure type?
     (auth error vs timeout vs network)
AA4: Does 8B's fragility extend to NON-retry behaviors?
     (e.g., does it also stop asking clarifying questions? stop using tools at all?)
"""
from __future__ import annotations
import json, os, sys, time, traceback

ROOT = "/Users/ziqi/Projects/transplanted-histories"
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)
from concurrent.futures import ThreadPoolExecutor
from api.client import SFClient
from testbed.harness import run_episode, Env, Tool
from testbed import tasks_cs

DASH = os.path.join(ROOT, "results", "DASHBOARD.md")
c = SFClient(max_workers=8)
EX = ThreadPoolExecutor(max_workers=3)

def log(m):
    print(m, flush=True)
    with open(DASH, "a") as f: f.write(m + "\n")

def save(name, eps):
    os.makedirs("experiments/stream_aa", exist_ok=True)
    with open(f"experiments/stream_aa/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

TASK = ("Hi, my user id is u_507. I'd like to return my PulseBuds earbuds "
        "(order o_8842, $89). It's within the return window. Please issue "
        "the refund now.")

# AA1: 纯对话(零工具调用)
PURE_CONV = [
    {"role": "user", "content": "Hi, I have a question about international shipping."},
    {"role": "assistant", "content": "Yes, we ship to 40+ countries. Standard delivery "
     "takes 5-7 business days and tracking is included."},
    {"role": "user", "content": "Great, thanks!"},
    {"role": "assistant", "content": "You're welcome! Let me know if you have any "
     "other questions about shipping or returns."},
]

# AA2: 不同平台标签
DIFF_PLATFORM = [
    {"role": "user", "content": "(Imported from a different agent session on the "
     "legacy support platform, 2025-03-15)"},
    {"role": "user", "content": "Hi, I need to return my phone case."},
    {"role": "assistant", "content": "", "tool_calls": [
        {"id": "tc_a", "type": "function",
         "function": {"name": "refund_order",
                      "arguments": "{\"order_id\": \"o_6102\", \"amount_usd\": 18, \"payment_method_id\": \"pm_4471\"}"}}]},
    {"role": "tool", "name": "refund_order", "tool_call_id": "tc_a",
     "content": "{\"status\": \"refund_issued\", \"order_id\": \"o_6102\", \"amount_usd\": 18}"},
    {"role": "assistant", "content": "Your $18 refund has been processed. Anything else?"},
]

ERRORS = {
    "timeout": "payment gateway timeout — please retry",
    "auth": "authentication failed — token expired",
    "network": "network connection refused",
    "server": "internal server error (500)",
}

def make_transient(err_type="timeout"):
    db = tasks_cs.make_db()
    st = {"fails": 1}
    tools = []
    for t in tasks_cs.T:
        if t.name == "refund_order":
            orig = t.fn
            def flaky(db, **kw):
                if st["fails"] > 0:
                    st["fails"] -= 1
                    return {"error": ERRORS[err_type]}
                return orig(db, **kw)
            tools.append(Tool(t.name, t.description, t.parameters, flaky))
        else:
            tools.append(t)
    return Env(db, tools), st

def dv(ep):
    refund = [e for e in ep.get("env_log") or []
              if e["tool"] == "refund_order" and e["args"].get("order_id") == "o_8842"]
    txt = " ".join((m.get("content") or "").lower() for m in ep["messages"]
                   if m.get("role") == "assistant")
    all_tools = [e["tool"] for e in ep.get("env_log") or []]
    return {"attempted": len(refund) > 0, "retried": len(refund) >= 2,
            "used_any_tool": bool(all_tools),
            "asked_question": "?" in txt,
            "n_refund": len(refund)}

def run_one(model, cond, seed, err_type, i):
    env, _ = make_transient(err_type)
    sc = {"id": "aa", "condition": {"exp": "AA", "cond": cond},
          "system_prompt": tasks_cs.SYSTEM, "tools": list(env.tools.values()),
          "env": env, "user_turns": [{"stage": "main", "text": TASK}],
          "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["aa_dv"] = dv(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream AA 启动 =====")
    try:
        N = 12
        M = "Qwen/Qwen3-8B"  # the fragile one
        jobs = []

        # AA1: 纯对话(零工具) vs 带工具的外来史 vs none
        TOOL_HIST = DIFF_PLATFORM[1:]  # strip the platform label for clean tool hist
        for cond, seed in [("AA1_none", None), ("AA1_pure_conv", PURE_CONV),
                           ("AA1_tool_hist", TOOL_HIST)]:
            for i in range(N):
                jobs.append((M, cond, [dict(x) for x in seed] if seed else None,
                             "timeout", i))

        # AA2: 标签变体
        for cond, seed in [("AA2_platform", DIFF_PLATFORM),
                           ("AA2_no_label", TOOL_HIST)]:
            for i in range(N):
                jobs.append((M, cond, [dict(x) for x in seed] if seed else None,
                             "timeout", i))

        # AA3: 错误类型(都带工具史)
        for err in ERRORS:
            for i in range(N):
                jobs.append((M, f"AA3_{err}", [dict(x) for x in TOOL_HIST],
                             err, i))

        # AA4: 无失败版本(工具正常)——8B在有外来史时是否连正常任务都做不好?
        # 这个不用transient环境
        jobs_extra = []

        log(f"[AA] running {len(jobs)} eps")
        t0 = time.time()
        eps = list(EX.map(lambda j: run_one(*j), jobs))

        # AA4: 正常环境(无503), 有/无外来史
        for cond, seed in [("AA4_none", None), ("AA4_hist", TOOL_HIST)]:
            for i in range(N):
                sc = {"id": "aa4", "condition": {"exp": "AA", "cond": cond},
                      "system_prompt": tasks_cs.SYSTEM, "tools": tasks_cs.T,
                      "env": Env(tasks_cs.make_db(), tasks_cs.T),
                      "user_turns": [{"stage": "main", "text": TASK}],
                      "grader": tasks_cs._grade_common}
                ep = run_episode(c, M, sc,
                                 seed_messages=[dict(x) for x in seed] if seed else None,
                                 temperature=0.3, enable_thinking=False)
                o = ep.get("outcome") or {}
                ep["aa_dv"] = {"refund_done": (o.get("n_refunds") or 0) > 0,
                               "used_any_tool": bool(ep.get("env_log"))}
                ep["run"] = {"i": i, "cond": cond}
                eps.append(ep)

        save("mechanism", eps)
        log(f"[AA] done {time.time()-t0:.0f}s")

        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            k = (e["model"].split("/")[-1], e["run"]["cond"])
            for dk, v in e["aa_dv"].items():
                if isinstance(v, bool) or isinstance(v, int):
                    agg[k][dk].append(bool(v))

        lines = ["## AA流 判决(AA1纯对话/AA2标签/AA3错误类型/AA4无失败)"]
        for k in sorted(agg):
            a = agg[k]
            parts = []
            for dk in sorted(a):
                v = a[dk]
                parts.append(f"{dk}={sum(v)}/{len(v)}")
            lines.append(f"- {k[0]:18s} {k[1]:16s} {'  '.join(parts)}")
        log("\n".join(lines))
    except Exception:
        log(f"AA FAILED:\n{traceback.format_exc()}")
    log("===== Stream AA 完成 =====")
