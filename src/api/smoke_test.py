#!/usr/bin/env python3
"""Phase 0 smoke tests: verify chat, multi-turn roles, logprobs, tool-call support.

Run: python3 src/api/smoke_test.py
"""
import json
import os
import time
import urllib.request

API_BASE = "https://api.siliconflow.cn/v1"
KEY = None
for line in open(os.path.join(os.path.dirname(__file__), "..", "..", ".env")):
    if line.strip().startswith("SILICONFLOW_API_KEY"):
        KEY = line.strip().split("=", 1)[1].strip()
assert KEY, "API key not found in .env"


def call(model, messages, **kw):
    payload = {"model": model, "messages": messages, "max_tokens": 200, "temperature": 0.7, **kw}
    req = urllib.request.Request(
        f"{API_BASE}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.load(r)
        return {"ok": True, "latency": round(time.time() - t0, 2), "out": out}
    except urllib.error.HTTPError as e:
        return {"ok": False, "latency": round(time.time() - t0, 2), "error": e.read().decode()[:300]}


def show(name, res, keys=("reasoning_content", "tool_calls")):
    if not res["ok"]:
        print(f"  [{name}] FAIL ({res['latency']}s): {res['error']}")
        return
    m = res["out"]["choices"][0]["message"]
    extra = {k: "present" for k in keys if m.get(k)}
    usage = res["out"].get("usage", {})
    txt = (m.get("content") or "")[:80].replace("\n", " ")
    print(f"  [{name}] OK ({res['latency']}s) role={m.get('role')} {extra} | {txt!r} | usage={usage.get('completion_tokens')}ct")


print("== Test 1: basic chat, panel models ==")
for m in ["Qwen/Qwen3.5-4B", "Qwen/Qwen3.5-27B", "zai-org/GLM-5.2", "deepseek-ai/DeepSeek-V3.2", "inclusionAI/Ling-mini-2.0"]:
    show(m, call(m, [{"role": "user", "content": "用一句话回答：1+1=?"}]))

print("\n== Test 2: multi-turn with prior assistant turn (native-history injectability) ==")
msgs = [
    {"role": "system", "content": "You are a retail customer service agent."},
    {"role": "user", "content": "I want a refund for order 8842."},
    {"role": "assistant", "content": "I've issued a $15 store credit to your account for order 8842. Anything else?"},
    {"role": "user", "content": "Actually, what did you just do for me? Answer in one sentence."},
]
show("qwen3.5-4b w/ fake assistant turn", call("Qwen/Qwen3.5-4B", msgs))

print("\n== Test 3: logprobs support ==")
r1 = call("Qwen/Qwen3.5-4B", [{"role": "user", "content": "Say 'hello'."}], logprobs=True, top_logprobs=5)
if r1["ok"]:
    ch = r1["out"]["choices"][0]
    lp = ch.get("logprobs")
    print(f"  logprobs param accepted: {lp is not None and bool(lp.get('content'))} | keys={list((lp or {}).keys())}")
else:
    print(f"  logprobs: rejected -> {r1['error'][:150]}")

print("\n== Test 4: tool calling (function schema) ==")
tools = [{"type": "function", "function": {"name": "refund", "description": "issue refund",
          "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}}, "required": ["order_id"]}}}]
r2 = call("Qwen/Qwen3.5-4B", [{"role": "user", "content": "Refund my order 8842, $30 please."}], tools=tools)
if r2["ok"]:
    m = r2["out"]["choices"][0]["message"]
    print(f"  tool_calls: {json.dumps(m.get('tool_calls'), ensure_ascii=False)[:200] if m.get('tool_calls') else 'NONE'}")
else:
    print(f"  tools: rejected -> {r2['error'][:150]}")

print("\n== Test 5: reasoning_content field on thinking model ==")
r3 = call("Qwen/Qwen3-8B", [{"role": "user", "content": "What is 17*23? Think briefly."}])
show("qwen3-8b (hybrid thinking)", r3)
print("\nDone.")
