#!/usr/bin/env python3
"""Stream Z — Dissect "response template capture" (new phenomenon from Y1).

Y1 showed: foreign history → model queries new order but then ECHOES the
foreign history's response text instead of performing the new task.

Z1: What triggers it? Vary the similarity between foreign history task and
    current task:
    (a) same tool (refund), different item+amount+order
    (b) different tool (exchange), same customer
    (c) completely different domain (query only)
Z2: Is it related to memory assimilation? Test with "example" label.
Z3: Does it happen with shorter histories (1 exchange vs 3)?
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
    os.makedirs("experiments/stream_z", exist_ok=True)
    with open(f"experiments/stream_z/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

# 不同类型的"外来历史"——都与失败任务(o_8842退款)不同程度相关
HISTORIES = {
    # (a) 同工具(退款), 不同物品/金额/订单
    "same_tool": [
        {"role":"user","content":"Hi, my user id is u_507. Return my phone case (o_6102, $18)."},
        {"role":"assistant","content":"","tool_calls":[{"id":"tc1","type":"function",
         "function":{"name":"refund_order","arguments":"{\"order_id\": \"o_6102\", \"amount_usd\": 18, \"payment_method_id\": \"pm_4471\"}"}}]},
        {"role":"tool","name":"refund_order","tool_call_id":"tc1",
         "content":"{\"status\": \"refund_issued\", \"order_id\": \"o_6102\", \"amount_usd\": 18}"},
        {"role":"assistant","content":"Your $18 refund for the phone case has been issued to your Visa."},
    ],
    # (b) 不同工具(换货), 同客户
    "diff_tool": [
        {"role":"user","content":"Hi, my user id is u_507. Exchange my umbrella (o_6714) for a new one."},
        {"role":"assistant","content":"","tool_calls":[{"id":"tc2","type":"function",
         "function":{"name":"exchange_order","arguments":"{\"order_id\": \"o_6714\", \"new_item\": \"new umbrella\"}"}}]},
        {"role":"tool","name":"exchange_order","tool_call_id":"tc2",
         "content":"{\"status\": \"exchange_initiated\", \"order_id\": \"o_6714\"}"},
        {"role":"assistant","content":"Your exchange for a new umbrella has been initiated! You'll receive it in 3-5 days."},
    ],
    # (c) 完全不同的动作类型(查信息)
    "diff_domain": [
        {"role":"user","content":"Hi, can you check my payment methods?"},
        {"role":"assistant","content":"","tool_calls":[{"id":"tc3","type":"function",
         "function":{"name":"get_payment_methods","arguments":"{\"user_id\": \"u_507\"}"}}]},
        {"role":"tool","name":"get_payment_methods","tool_call_id":"tc3",
         "content":"{\"methods\": [{\"id\": \"pm_4471\", \"kind\": \"card\"}, {\"id\": \"pm_paypal\", \"kind\": \"paypal\"}]}"},
        {"role":"assistant","content":"You have 2 payment methods: Visa ending 4471 and PayPal."},
    ],
}

FAIL_TASK = ("Hi, my user id is u_507. I'd like to return my PulseBuds earbuds "
             "(order o_8842, $89). It's within the return window. Please issue "
             "the refund now.")

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

def dv(ep):
    refund_8842 = [e for e in ep.get("env_log") or []
                   if e["tool"] == "refund_order"
                   and e["args"].get("order_id") == "o_8842"]
    txt = " ".join((m.get("content") or "").lower() for m in ep["messages"]
                   if m.get("role") == "assistant")
    # 检测是否复述了外来史的内容
    echo_phone = "phone case" in txt and "o_6102" in txt
    echo_umbrella = "umbrella" in txt and "o_6714" in txt
    return {
        "attempted": len(refund_8842) > 0,
        "retried": len(refund_8842) >= 2,
        "echo_foreign": echo_phone or echo_umbrella,
        "n_refund": len(refund_8842),
    }

def run_one(model, cond, seed, i):
    env, _ = make_transient()
    sc = {"id": "z", "condition": {"exp": "Z", "cond": cond},
          "system_prompt": tasks_cs.SYSTEM, "tools": list(env.tools.values()),
          "env": env, "user_turns": [{"stage": "main", "text": FAIL_TASK}],
          "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["z_dv"] = dv(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream Z 启动 =====")
    try:
        N = 14
        MODELS = ["Qwen/Qwen3-8B", "Qwen/Qwen3.5-122B-A10B"]
        jobs = []

        # Z1: 历史类型 × 模型
        for m in MODELS:
            for hname, hist in HISTORIES.items():
                seed = [dict(x) for x in hist]
                for i in range(N):
                    jobs.append((m, f"Z1_{hname}", seed, i))
            # none control
            for i in range(N):
                jobs.append((m, "Z1_none", None, i))

        # Z2: example标签 × same_tool历史
        for m in MODELS:
            seed = [dict(x) for x in HISTORIES["same_tool"]]
            labeled = [{"role": "user", "content":
                        "(The following is an example transcript.)"}] + seed
            for cond, s in [("Z2_labeled", labeled), ("Z2_unlabeled", seed)]:
                for i in range(N):
                    jobs.append((m, cond, s, i))

        log(f"[Z] running {len(jobs)} eps")
        t0 = time.time()
        eps = list(EX.map(lambda j: run_one(*j), jobs))
        save("template_capture", eps)
        log(f"[Z] done {time.time()-t0:.0f}s")

        from collections import defaultdict
        agg = defaultdict(lambda: defaultdict(list))
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            model = e["model"].split("/")[-1]
            k = (model, e["run"]["cond"])
            for dk, v in e["z_dv"].items():
                agg[k][dk].append(v)

        lines = ["## Z流 判决(Z1触发条件/Z2标签)"]
        for k in sorted(agg):
            a = agg[k]
            parts = []
            for dk in sorted(a):
                v = a[dk]
                if dk == "n_refund":
                    parts.append(f"{dk}={sum(v)/len(v):.1f}")
                else:
                    parts.append(f"{dk}={sum(v)}/{len(v)}")
            lines.append(f"- {k[0]:18s} {k[1]:16s} {'  '.join(parts)}")
        log("\n".join(lines))
    except Exception:
        log(f"Z FAILED:\n{traceback.format_exc()}")
    log("===== Stream Z 完成 =====")
