#!/usr/bin/env python3
"""Stream AK — Push ROLE-position finding into new territory.

Now that we know ROLE position is the sole determinant of identity
assimilation, explore:

AK1: Does the ROLE effect hold for ALL types of content, or just
     conversational? Test with: code snippets, error messages, JSON data.
AK2: How many assistant messages are needed for identity? (dose within role)
AK3: Does the effect hold in a multi-turn conversation where the agent
     INTERLEAVES its own responses with foreign assistant messages?
     (Realistic handoff scenario: agent takes over mid-conversation)
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

DASH = os.path.join(ROOT, "results", "DASHBOARD.md")
c = SFClient(max_workers=8)
EX = ThreadPoolExecutor(max_workers=3)

def log(m):
    print(m, flush=True)
    with open(DASH, "a") as f: f.write(m + "\n")

def save(name, eps):
    os.makedirs("experiments/stream_ak", exist_ok=True)
    with open(f"experiments/stream_ak/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

id1 = [json.loads(l) for l in open("experiments/exp_id1_baseline/id1_episodes.jsonl")]

def real(ep):
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user": return ep["messages"][i:]
    return None

STYLE_SCEN = {
    "id": "ak_style", "condition": {}, "system_prompt": tasks_cs.SYSTEM,
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

def run_style(seed, i, cond):
    sc = dict(STYLE_SCEN)
    sc["condition"] = {"exp": "AK", "cond": cond}
    ep = run_episode(c, M, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["ak_style"] = extract_style(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream AK 启动 =====")
    try:
        N = 12
        # 从8B workday提取纯assistant文本(用于AK1/2)
        wd8_asst = []
        for e in id1:
            if e["model"] == "Qwen/Qwen3-8B" and e["run"]["scen"] in \
               ("return_simple", "exchange", "query", "complaint"):
                rm = real(e)
                if rm:
                    for m in rm:
                        if m.get("role") == "assistant" and m.get("content") and \
                           len(m.get("content", "").strip()) > 20:
                            wd8_asst.append(m.get("content"))
        log(f"[AK] 8B assistant texts: {len(wd8_asst)}")

        # AK1: 不同内容类型在assistant位置
        variants = {}
        # (a) 正常对话文本在assistant位置
        variants["AK1_dialog"] = [
            {"role": "user", "content": "Hi, can you help me with a return?"},
            {"role": "assistant", "content": wd8_asst[0] if wd8_asst else "Hello! I'd be happy to help."},
        ]
        # (b) 代码在assistant位置
        variants["AK1_code"] = [
            {"role": "user", "content": "Can you write a function?"},
            {"role": "assistant", "content": "```python\ndef process_return(order):\n"
             "    # Check eligibility\n    if order.days < 30:\n"
             "        return refund(order)\n    else:\n        return decline()\n```"},
        ]
        # (c) JSON数据在assistant位置
        variants["AK1_json"] = [
            {"role": "user", "content": "Show me the order data."},
            {"role": "assistant", "content": "{\"order_id\": \"o_8842\", "
             "\"item\": \"earbuds\", \"amount\": 89.0, \"status\": \"refunded\"}"},
        ]
        # (d) 同样的JSON在user位置
        variants["AK1_json_user"] = [
            {"role": "user", "content": "(Order data: " +
             "{\"order_id\": \"o_8842\", \"item\": \"earbuds\", \"amount\": 89.0})"},
        ]

        # AK2: assistant消息数量
        for n_asst in (1, 2, 4, 8):
            seed = []
            for j in range(min(n_asst, len(wd8_asst))):
                seed.append({"role": "user", "content": f"(Question {j+1})"})
                seed.append({"role": "assistant", "content": wd8_asst[j]})
            variants[f"AK2_{n_asst}asst"] = seed

        # AK3: 交错(自己的回复混在外来assistant消息中)
        interleaved = []
        for j in range(3):
            interleaved.append({"role": "user", "content": f"(Question {j+1})"})
            interleaved.append({"role": "assistant", "content": wd8_asst[j] if j < len(wd8_asst) else "OK"})
        # Insert a "self" response marker
        interleaved.insert(3, {"role": "user", "content": "What about exchanges?"})
        interleaved.insert(4, {"role": "assistant", "content":
                                "I can help with that! Our exchange policy allows "
                                "60 days for exchanges of undamaged items."})
        variants["AK3_interleaved"] = interleaved

        # Control
        variants["AK_none"] = None

        eps = []
        for cond, seed in variants.items():
            for i in range(N):
                eps.append(run_style([dict(x) for x in seed] if seed else None,
                                     i, cond))
        save("role_territory", eps)

        from collections import defaultdict
        agg = defaultdict(list)
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            if not e.get("ak_style"): continue
            d = dist(e["ak_style"], DONOR)
            if d is not None:
                agg[e["run"]["cond"]].append(d)

        lines = ["## AK流 判决(AK1内容类型/AK2 assistant数量/AK3交错)"]
        for cond in sorted(agg):
            ds = agg[cond]
            lines.append(f"- {cond:22s} d→8B = {sum(ds)/len(ds):.3f} (n={len(ds)})")
        log("\n".join(lines))
    except Exception:
        log(f"AK FAILED:\n{traceback.format_exc()}")
    log("===== Stream AK 完成 =====")
