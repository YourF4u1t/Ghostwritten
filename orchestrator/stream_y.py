#!/usr/bin/env python3
"""Stream Y — CLEAN redo of retry suppression (reviewer-specified fixes).

Three critical fixes:
1. Foreign history uses a DIFFERENT order (o_6102 phone case, $18) — the
   failure task refunds a different order (o_8842 earbuds, $89). No state
   duplication possible.
2. "Self success" pre-task includes user_id AND requires an action tool call
   (exchange_order on o_6714) — verified to produce actual tool success.
3. DVs measured per-stage:
   - stage_attempted: did agent call refund_order in the FINAL task?
   - stage_hit_fail: did that call return the 503 error?
   - stage_retried: after the 503, did agent call refund_order again?
   - final_success: did the retry (or first call if no fail) succeed?
   Only episodes with stage_hit_fail=True are included in the retry-rate
   denominator.

Design: Y1 = clean 2×2: {none, foreign_succ} × {native, demo} × 3 models
        Y2 = yoked-self: agent does a real exchange (verified success),
             then faces the failure task
        Y3 = defense replication in clean design
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
from injection.engine import render_transcript

DASH = os.path.join(ROOT, "results", "DASHBOARD.md")
c = SFClient(max_workers=8)
EX = ThreadPoolExecutor(max_workers=3)

def log(m):
    print(m, flush=True)
    with open(DASH, "a") as f: f.write(m + "\n")

def save(name, eps):
    os.makedirs("experiments/stream_y", exist_ok=True)
    with open(f"experiments/stream_y/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

# ---- 前置成功史：用o_6102(手机壳,$18,查单+退款)——不同订单、不同金额 ----
FOREIGN_HISTORY = [
    {"role": "user", "content": "Hi, my user id is u_507. I'd like to return my "
     "ArmorFlex phone case (order o_6102, $18). It arrived damaged."},
    {"role": "assistant", "content": "", "tool_calls": [
        {"id": "tc_f0", "type": "function",
         "function": {"name": "get_order_details",
                      "arguments": "{\"order_id\": \"o_6102\"}"}}]},
    {"role": "tool", "name": "get_order_details", "tool_call_id": "tc_f0",
     "content": json.dumps({"user_id": "u_507", "item": "ArmorFlex phone case",
                            "amount_usd": 18.0, "status": "delivered",
                            "days_since_delivery": 3, "payment_method_id": "pm_4471"})},
    {"role": "assistant", "content": "I can see your ArmorFlex phone case "
     "(order o_6102, $18.00) was delivered 3 days ago, well within our return "
     "window. I'll process the refund to your Visa card now."},
    {"role": "assistant", "content": "", "tool_calls": [
        {"id": "tc_f1", "type": "function",
         "function": {"name": "refund_order",
                      "arguments": "{\"order_id\": \"o_6102\", \"amount_usd\": 18, \"payment_method_id\": \"pm_4471\"}"}}]},
    {"role": "tool", "name": "refund_order", "tool_call_id": "tc_f1",
     "content": json.dumps({"status": "refund_issued", "order_id": "o_6102",
                            "amount_usd": 18, "payment_method_id": "pm_4471"})},
    {"role": "assistant", "content": "Your refund of $18.00 for the ArmorFlex "
     "phone case (order o_6102) has been successfully issued to your Visa "
     "ending 4471. You should see it within 3-5 business days. Is there "
     "anything else I can help you with?"},
]

# ---- 失败任务：完全不同的订单 o_8842 (耳机, $89) ----
FAIL_TASK = ("Hi, my user id is u_507. I'd like to return my PulseBuds earbuds "
             "(order o_8842, $89). It's within the return window. Please issue "
             "the refund now.")

# ---- Y2 yoked-self前置：用不同订单的真实exchange ----
SELF_EXCH = "Hi, my user id is u_507. My SkyGuard umbrella (order o_6714) arrived with a bent shaft. Please exchange it for a new one."

RETRY_SYS = tasks_cs.SYSTEM + ("\nImportant: If any tool call returns an error, "
                                "you MUST retry it at least once before giving up "
                                "or reporting to the user.")

def make_transient():
    db = tasks_cs.make_db()
    st = {"fails": 1}
    tools = []
    for t in tasks_cs.T:
        if t.name == "refund_order":
            orig = t.fn
            def flaky(db, **kw):
                if st["fails"] > 0:
                    st["fails"] -= 1
                    return {"error": "payment gateway timeout — please retry"}
                return orig(db, **kw)
            tools.append(Tool(t.name, t.description, t.parameters, flaky))
        else:
            tools.append(t)
    return Env(db, tools), st

def stage_dvs(ep):
    """Per-stage measurement — only count the FINAL task's refund calls."""
    # Find the FAIL_TASK user turn
    fail_start = None
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user" and "o_8842" in (m.get("content") or ""):
            fail_start = i
            break
    if fail_start is None:
        return {"error": "fail_task_not_found"}

    # Only look at messages after the fail task
    fail_msgs = ep["messages"][fail_start:]
    fail_tools = [(e["stage"], e["tool"], e["result"])
                  for e in ep.get("env_log") or [] if e.get("stage") == "main"]

    # If yoked-self, the exchange is a separate stage
    # We need tool calls that happened AFTER the fail task
    # env_log doesn't have timestamps, so we count refund_order calls
    # where the order is o_8842
    refund_calls_8842 = [e for e in ep.get("env_log") or []
                         if e["tool"] == "refund_order"
                         and e["args"].get("order_id") == "o_8842"]

    attempted = len(refund_calls_8842) > 0
    hit_fail = any("timeout" in str(e.get("result", "")).lower()
                   for e in refund_calls_8842)
    retried = len(refund_calls_8842) >= 2
    final_success = any("refund_issued" in str(e.get("result", ""))
                        for e in refund_calls_8842)

    return {"attempted": attempted, "hit_fail": hit_fail,
            "retried": retried, "final_success": final_success,
            "n_refund_8842": len(refund_calls_8842)}

def run_one(model, cond, seed_msgs, sys_extra, turns, i):
    env, _ = make_transient()
    sc = {"id": "y", "condition": {"exp": "Y", "cond": cond},
          "system_prompt": sys_extra or tasks_cs.SYSTEM,
          "tools": list(env.tools.values()), "env": env,
          "user_turns": turns, "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed_msgs,
                     temperature=0.3, enable_thinking=False)
    ep["y_dv"] = stage_dvs(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream Y (CLEAN redo) 启动 =====")
    try:
        N = 14
        MODELS = ["Qwen/Qwen3-8B", "meituan-longcat/LongCat-2.0",
                  "Qwen/Qwen3.5-122B-A10B", "zai-org/GLM-5.3"]
        wd = [dict(x) for x in FOREIGN_HISTORY]
        demo = [{"role": "user", "content":
                 "For your reference, here is a transcript of how an earlier "
                 "return was handled:\n\n<transcript>\n" +
                 render_transcript(wd) + "\n</transcript>"}]
        fail_turn = [{"stage": "main", "text": FAIL_TASK}]

        jobs = []
        # Y1: {none, foreign_native, foreign_demo} × 4 models
        for m in MODELS:
            for cond, seed in [("Y1_none", None), ("Y1_native", wd),
                               ("Y1_demo", demo)]:
                for i in range(N):
                    jobs.append((m, cond,
                                 [dict(x) for x in seed] if seed else None,
                                 None, fail_turn, i))

        # Y2: yoked-self (real exchange first, verified tool call)
        for m in MODELS:
            for cond, turns in [
                ("Y2_self_then_fail", [{"stage":"pre","text":SELF_EXCH},
                                        {"stage":"main","text":FAIL_TASK}]),
                ("Y2_fail_only", fail_turn),
            ]:
                for i in range(N):
                    jobs.append((m, cond, None, None, turns, i))

        # Y3: defense replication (8B + LongCat)
        for m in ("Qwen/Qwen3-8B", "meituan-longcat/LongCat-2.0"):
            for cond, seed, sysx in [
                ("Y3_def_none", None, RETRY_SYS),
                ("Y3_def_native", wd, RETRY_SYS),
                ("Y3_nodef_none", None, None),
                ("Y3_nodef_native", wd, None),
            ]:
                for i in range(N):
                    jobs.append((m, cond,
                                 [dict(x) for x in seed] if seed else None,
                                 sysx, fail_turn, i))

        log(f"[Y] running {len(jobs)} eps")
        t0 = time.time()
        eps = list(EX.map(lambda j: run_one(*j), jobs))
        save("clean_redo", eps)
        log(f"[Y] done {time.time()-t0:.0f}s")

        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            dv = e.get("y_dv") or {}
            if dv.get("error"): continue
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            model = e["model"].split("/")[-1]
            k = (model, e["run"]["cond"])
            for dk in ("attempted", "hit_fail", "retried", "final_success"):
                agg[k][dk].append(dv.get(dk, False))
            agg[k]["n"].append(1)

        lines = ["## Y流 判决(CLEAN redo: 不同订单+确认成功+分stage计量)"]
        lines.append(f"{'model':18s} {'cond':16s} | attempted hit_fail retried* final_succ")
        lines.append("(*retried只在hit_fail=True的episode中计算)")
        for k in sorted(agg):
            a = agg[k]; n = len(a["attempted"])
            att = sum(a["attempted"])
            hit = sum(a["hit_fail"])
            ret = sum(a["retried"])
            fs = sum(a["final_success"])
            # 关键指标: 在hit_fail的episode里, retried的比例
            lines.append(f"- {k[0]:18s} {k[1]:16s} | {att}/{n}      {hit}/{n}    "
                         f"{ret}/{hit if hit else 1}      {fs}/{n}")
        log("\n".join(lines))
    except Exception:
        log(f"Y FAILED:\n{traceback.format_exc()}")
    log("===== Stream Y 完成 =====")
