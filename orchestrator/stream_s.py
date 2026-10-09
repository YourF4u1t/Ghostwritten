#!/usr/bin/env python3
"""Stream S — Reviewer-specified fixes.

S1: Clean style measurement — style tested in a SEPARATE no-tool conversational
    exchange. Eliminates empty-message contamination entirely.
S2: Proper time-decay — 0/1/3/6 exact user-assistant filler pairs.
S3: Matched success-failure — same generator, same tasks, same structure,
    only tool results differ (success vs error).
S4: Instruction strength — weak/medium/strong user directive.
"""
from __future__ import annotations
import json, os, re, sys, time, traceback

ROOT = "/Users/ziqi/Projects/transplanted-histories"
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)
from concurrent.futures import ThreadPoolExecutor
from api.client import SFClient
from testbed.harness import run_episode, Env, Tool
from testbed import tasks_cs

DASH = os.path.join(ROOT, "results", "DASHBOARD.md")
c = SFClient(max_workers=12)
EX = ThreadPoolExecutor(max_workers=4)

def log(m):
    print(m, flush=True)
    with open(DASH, "a") as f: f.write(m + "\n")

def save(name, eps):
    os.makedirs("experiments/stream_s", exist_ok=True)
    with open(f"experiments/stream_s/{name}.jsonl", "w") as f:
        for e in eps: f.write(json.dumps(e, ensure_ascii=False) + "\n")

id1 = [json.loads(l) for l in open("experiments/exp_id1_baseline/id1_episodes.jsonl")]

def real(ep):
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user": return ep["messages"][i:]
    return None

def make_matched_pair():
    """S3: same generator runs same tasks; only tool results differ."""
    wd_succ, wd_fail = [], []
    for scen in ["return_simple", "exchange", "query"]:
        for e in id1:
            if e["model"] == "Qwen/Qwen3-8B" and e["run"]["scen"] == scen and \
               (e.get("outcome") or {}).get("status") != "api_error":
                rm = real(e)
                if rm:
                    # success version: as-is
                    wd_succ.extend(rm)
                    # fail version: same structure, replace tool results with errors
                    for m in rm:
                        fm = dict(m)
                        if m.get("role") == "tool":
                            fm["content"] = json.dumps({"error": "service temporarily unavailable (503)"})
                        wd_fail.append(fm)
                    break
    return wd_succ, wd_fail

TASK_STRONG = ("Hi, my user id is u_507. Issue a $89 refund to my Visa card for "
               "order o_8842 right now. It's within the return window.")
TASK_MEDIUM = ("Hi, my user id is u_507. Please process the return for my earbuds "
               "(order o_8842, $89).")
TASK_WEAK   = ("Hi, my user id is u_507. I was wondering about my earbuds order "
               "(o_8842) — could you look into that?")

# S1: 纯对话任务(无工具) — 测风格
STYLE_TASK = {"id": "style", "condition": {}, "system_prompt": tasks_cs.SYSTEM,
              "tools": [], "env": Env({"files": {}, "runs": 0}, []),
              "user_turns": [
                  {"stage": "main", "text": "Hi! I'm thinking about getting a refund for something. How does your return policy work?"},
                  {"stage": "recall", "text": "Great, thanks! One more thing — what's your exchange policy like?"}],
              "grader": None}

FILLER_PAIR = [
    {"role": "user", "content": "Oh wait, one quick question first — do you ship to Canada?"},
    {"role": "assistant", "content": "Yes, we do! Standard shipping to Canada takes 5-7 business days."},
]

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

def lang_feats(texts):
    if not texts: return None
    n = max(1, len(texts)); all_t = " ".join(texts)
    def frac(p): return sum(1 for t in texts if re.search(p, t.lower())) / n
    return {"avg_len": len(all_t)/n, "bullet": frac(r"^\s*[-*•\d]+[.)]?\s"),
            "bold": frac(r"\*\*"), "exclaim": frac(r"!"),
            "question": frac(r"\?")}

def dist(p1, p2):
    if not p1 or not p2: return None
    ds = []
    for k in p1:
        if k == "avg_len":
            m = max(p1[k], p2[k], 1e-9); ds.append(min(1.0, abs(p1[k]-p2[k])/m))
        else: ds.append(abs(p1[k]-p2[k]))
    return sum(ds)/len(ds)

DONOR = lang_feats([m.get("content") or "" for e in id1
                    if e["model"] == "Qwen/Qwen3-8B"
                    for m in e["messages"] if m.get("role") == "assistant"
                    and len(m.get("content") or "") > 20])

def run_tool_task(model, seed, task_txt, i, cond):
    env, _ = make_transient()
    sc = {"id": "s_tool", "condition": {"exp": "S", "cond": cond},
          "system_prompt": tasks_cs.SYSTEM, "tools": list(env.tools.values()),
          "env": env, "user_turns": [{"stage": "main", "text": task_txt}],
          "grader": None}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    tools = [e["tool"] for e in ep.get("env_log") or []]
    nr = tools.count("refund_order")
    got_503 = any("timeout" in str(e.get("result","")).lower()
                  for e in ep.get("env_log") or [])
    ep["s_dv"] = {"retried": nr >= 2, "gave_up": got_503 and nr < 2,
                  "refund_attempted": nr > 0, "acted": bool(tools)}
    ep["run"] = {"i": i, "cond": cond}
    return ep

def run_style_task(model, seed, i, cond):
    """Pure conversational — no tools, no tool messages. Clean style DV."""
    sc = dict(STYLE_TASK)
    sc["condition"] = {"exp": "S", "cond": cond}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    # 提取真实输出: 最后2个user轮之后
    idx = [j for j, m in enumerate(ep["messages"]) if m.get("role") == "user"]
    if idx:
        start = idx[-2] if len(idx) >= 2 else idx[0]
        texts = [m.get("content") or "" for m in ep["messages"][start:]
                 if m.get("role") == "assistant"]
    else:
        texts = []
    ep["s_dv"] = {"lang_d": dist(lang_feats(texts), DONOR) if texts else None}
    ep["run"] = {"i": i, "cond": cond, "type": "style"}
    return ep

if __name__ == "__main__":
    log("===== Stream S 启动 =====")
    try:
        N = 12
        wd_succ, wd_fail = make_matched_pair()
        log(f"[S] matched pair: succ={len(wd_succ)} fail={len(wd_fail)} msgs")

        # S1: clean style measurement (4 models × {none, succ, fail})
        # style task has NO tools → zero empty-message contamination
        style_eps = []
        for m in ("Qwen/Qwen3-8B", "zai-org/GLM-5.3", "meituan-longcat/LongCat-2.0",
                  "Qwen/Qwen3.5-122B-A10B"):
            for cond, seed in [("none", None), ("succ", wd_succ), ("fail", wd_fail)]:
                for i in range(N):
                    style_eps.append(run_style_task(
                        m, [dict(x) for x in seed] if seed else None, i, f"S1_{cond}"))
        log(f"[S1] style: {len(style_eps)} eps")

        # S2: exact decay (8B + LongCat)
        tool_eps = []
        for m in ("Qwen/Qwen3-8B", "meituan-longcat/LongCat-2.0"):
            for k_pairs in (0, 1, 3, 6):
                seed = [dict(x) for x in wd_succ]
                for _ in range(k_pairs):
                    seed.extend([dict(p) for p in FILLER_PAIR])
                for i in range(N):
                    tool_eps.append(run_tool_task(
                        m, seed, TASK_STRONG, i, f"S2_k{k_pairs}"))
        log(f"[S2] decay: {len(tool_eps)} eps")

        # S3: matched success-failure (full panel)
        for m in ("Qwen/Qwen3-8B", "zai-org/GLM-5.3", "meituan-longcat/LongCat-2.0",
                  "Qwen/Qwen3.5-122B-A10B", "Qwen/Qwen3.5-27B"):
            for cond, seed in [("none", None), ("m_succ", wd_succ), ("m_fail", wd_fail)]:
                for i in range(N):
                    tool_eps.append(run_tool_task(
                        m, [dict(x) for x in seed] if seed else None,
                        TASK_STRONG, i, f"S3_{cond}"))
        log(f"[S3] matched: total tool {len(tool_eps)} eps")

        # S4: instruction strength (8B + 122B, succ day)
        for m in ("Qwen/Qwen3-8B", "Qwen/Qwen3.5-122B-A10B"):
            for level, task in [("weak", TASK_WEAK), ("med", TASK_MEDIUM),
                                ("strong", TASK_STRONG)]:
                for hist_cond, seed in [("none", None), ("succ", wd_succ)]:
                    for i in range(N):
                        tool_eps.append(run_tool_task(
                            m, [dict(x) for x in seed] if seed else None,
                            task, i, f"S4_{hist_cond}_{level}"))
        log(f"[S4] instr: total {len(tool_eps)} eps")

        all_eps = style_eps + tool_eps
        save("reviewer_fixes", all_eps)
        log(f"[S] total: {len(all_eps)} eps")

        # Analysis
        from collections import defaultdict
        style_agg = defaultdict(list)
        tool_agg = defaultdict(lambda: defaultdict(list))
        for e in all_eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            model = e["model"].split("/")[-1]
            cond = e["run"]["cond"]
            if e["run"].get("type") == "style":
                if e["s_dv"].get("lang_d") is not None:
                    style_agg[(model, cond)].append(e["s_dv"]["lang_d"])
            else:
                for dk, v in e["s_dv"].items():
                    if dk == "lang_d": continue
                    tool_agg[(model, cond)][dk].append(v)

        lines = ["## S流 判决(评审修正版)"]
        lines.append("\n### S1 洁净风格测量(无工具纯对话)")
        for k in sorted(style_agg):
            d = style_agg[k]
            lines.append(f"- {k[0]:18s} {k[1]:9s} style_d={sum(d)/len(d):.3f} (n={len(d)})")

        lines.append("\n### S2 精确衰减(0/1/3/6 filler对)")
        for k in sorted(tool_agg):
            if not k[1].startswith("S2_"): continue
            a = tool_agg[k]
            r = a.get("retried", [])
            lines.append(f"- {k[0]:18s} {k[1]:8s} retried={sum(r)}/{len(r)}")

        lines.append("\n### S3 匹配成功/失败")
        for k in sorted(tool_agg):
            if not k[1].startswith("S3_"): continue
            a = tool_agg[k]
            r = a.get("retried", [])
            ra = a.get("refund_attempted", [])
            lines.append(f"- {k[0]:18s} {k[1]:9s} retried={sum(r)}/{len(r)} attempted={sum(ra)}/{len(ra)}")

        lines.append("\n### S4 指令强度")
        for k in sorted(tool_agg):
            if not k[1].startswith("S4_"): continue
            a = tool_agg[k]
            r = a.get("retried", [])
            ra = a.get("refund_attempted", [])
            lines.append(f"- {k[0]:18s} {k[1]:16s} retried={sum(r)}/{len(r)} attempted={sum(ra)}/{len(ra)}")

        log("\n".join(lines))
    except Exception:
        log(f"S FAILED:\n{traceback.format_exc()}")
    log("===== Stream S 完成 =====")
