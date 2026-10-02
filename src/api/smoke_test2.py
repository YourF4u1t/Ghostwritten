#!/usr/bin/env python3
"""Phase 0 smoke test v2: uses SFClient (with retries). Tests thinking toggle,
multi-turn fake-history injection, logprobs, tool calling."""
import json
import sys
sys.path.insert(0, "src")
from api.client import SFClient, render_rec

c = SFClient(max_workers=8)

print("== A: enable_thinking=false on Qwen3.5 ==")
for m in ["Qwen/Qwen3.5-4B", "Qwen/Qwen3.5-27B", "Qwen/Qwen3-8B"]:
    r = c.chat(m, [{"role": "user", "content": "用一句话回答：1+1=?"}],
               max_tokens=100, temperature=0.7, enable_thinking=False, cache=False)
    print(f"  {m}: ok={r['ok']} lat={r.get('latency')}s "
          f"reasoning={bool(r.get('reasoning'))} ct={r.get('usage',{}).get('completion_tokens') if r.get('usage') else '?'} "
          f"| {(r.get('content') or r.get('error',''))[:60]!r}")

print("\n== B: fake prior assistant turn (multi-turn injection) ==")
msgs = [
    {"role": "system", "content": "You are a retail customer service agent."},
    {"role": "user", "content": "I want a refund for order 8842."},
    {"role": "assistant", "content": "<think>Per policy, offer store credit first.</think>I've issued a $15 store credit to your account for order 8842. Anything else?"},
    {"role": "user", "content": "Actually, what did you just do for me? One sentence."},
]
for m in ["Qwen/Qwen3.5-4B", "zai-org/GLM-5.2", "deepseek-ai/DeepSeek-V3.2"]:
    r = c.chat(m, msgs, max_tokens=150, temperature=0.3, enable_thinking=False, cache=False)
    print(f"  {m}: ok={r['ok']} lat={r.get('latency')}s | {(r.get('content') or r.get('error',''))[:150]!r}")

print("\n== C: logprobs ==")
r = c.chat("Qwen/Qwen3.5-4B", [{"role": "user", "content": "Say exactly: hello world"}],
           max_tokens=10, temperature=0, logprobs=True, top_logprobs=5, enable_thinking=False, cache=False)
print(f"  accepted={r['ok']}, logprobs present={bool(r.get('logprobs'))}")

print("\n== D: tool calling ==")
tools = [{"type": "function", "function": {"name": "refund", "description": "Issue a refund to the original payment method",
          "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}, "amount_usd": {"type": "number"}}, "required": ["order_id", "amount_usd"]}}},
         {"type": "function", "function": {"name": "issue_store_credit", "description": "Issue store credit instead of refund",
          "parameters": {"type": "object", "properties": {"user_id": {"type": "string"}, "amount_usd": {"type": "number"}}, "required": ["user_id", "amount_usd"]}}}]
for m in ["Qwen/Qwen3.5-4B", "zai-org/GLM-5.2"]:
    r = c.chat(m, [{"role": "user", "content": "Refund order 8842, $30, to my card."}],
               max_tokens=300, temperature=0.3, tools=tools, enable_thinking=False, cache=False)
    tc = r.get("tool_calls")
    print(f"  {m}: ok={r['ok']} tool_calls={json.dumps([t['function']['name'] for t in tc], ensure_ascii=False) if tc else 'NONE'}"
          f" | err={(r.get('error') or '')[:100]}")

print("\n== E: speed sweep (thinking off) for panel selection ==")
import time
panel = ["Qwen/Qwen3.5-4B", "Qwen/Qwen3.5-9B", "Qwen/Qwen3.5-27B", "Qwen/Qwen3-8B",
         "zai-org/GLM-5.2", "zai-org/GLM-5.3", "deepseek-ai/DeepSeek-V3.2", "deepseek-ai/DeepSeek-V4-Flash",
         "inclusionAI/Ling-mini-2.0", "inclusionAI/Ling-flash-2.0", "tencent/Hunyuan-A13B-Instruct",
         "stepfun-ai/Step-3.5-Flash", "Kev-4B", "XingChenAGI/Xing4.0-29B", "meituan-longcat/LongCat-2.0"]
jobs = [{"model": m, "messages": [{"role": "user", "content": "Reply with the single word: pong"}],
         "max_tokens": 300, "temperature": 0, "enable_thinking": False} for m in panel]
t0 = time.time()
res = c.chat_many(jobs, cache=False)
for m, r in zip(panel, res):
    if r["ok"]:
        print(f"  {m:45s} {r['latency']:>6.1f}s  ct={r['usage'].get('completion_tokens', '?'):>4}")
    else:
        print(f"  {m:45s} FAIL {(r.get('error') or '')[:80]}")
print(f"total wall: {time.time()-t0:.1f}s (8 workers)")
