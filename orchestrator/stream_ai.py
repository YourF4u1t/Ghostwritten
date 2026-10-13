#!/usr/bin/env python3
"""Stream AI — Minimum identity unit + cross-session persistence.

AI1: What is the MINIMUM amount of foreign history that triggers identity
     assimilation? Test: 1 exchange (2 msgs), 2 exchanges (4 msgs),
     1 full task (~8 msgs), full workday (~20 msgs).
AI2: Cross-session persistence — after assimilating in session 1, if the
     model starts a completely NEW session (no history), does the style
     persist? (Tests whether it's a context effect or a weight-like change.)
AI3: Competition — if the model has BOTH its own recent history AND foreign
     history, which wins for style?
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
    os.makedirs("experiments/stream_ai", exist_ok=True)
    with open(f"experiments/stream_ai/{name}.jsonl", "w") as f:
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

# 不同剂量的外来史(从完整工作日截取)
def dose(wd, n_msgs):
    """Take first n_msgs from workday, ensuring it ends with an assistant msg."""
    cut = wd[:n_msgs]
    while cut and cut[-1].get("role") == "user":
        cut.pop()
    return cut

STYLE_SCEN = {
    "id": "ai_style", "condition": {}, "system_prompt": tasks_cs.SYSTEM,
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
M = "Qwen/Qwen3.5-122B-A10B"  # clean subject (assimilates but not baseline-noisy)

def run_style(seed, i, cond, model=M):
    sc = dict(STYLE_SCEN)
    sc["condition"] = {"exp": "AI", "cond": cond}
    ep = run_episode(c, model, sc, seed_messages=seed,
                     temperature=0.3, enable_thinking=False)
    ep["ai_style"] = extract_style(ep)
    ep["run"] = {"i": i, "cond": cond}
    return ep

if __name__ == "__main__":
    log("===== Stream AI 启动 =====")
    try:
        N = 12
        wd8 = workday("Qwen/Qwen3-8B", 4)
        log(f"[AI] workday={len(wd8)} msgs")
        eps = []

        # AI1: dose-response of identity
        for n_msgs in (0, 2, 4, 8, 16, len(wd8)):
            seed = dose(wd8, n_msgs) if n_msgs > 0 else None
            label = f"AI1_{n_msgs}msg"
            for i in range(N):
                eps.append(run_style([dict(x) for x in seed] if seed else None,
                                     i, label))
        log(f"[AI1] dose: {len(eps)} eps")

        # AI2: cross-session persistence
        # Phase 1: carry workday, do style task (get assimilated output)
        p1_eps = []
        for i in range(N):
            ep = run_style([dict(x) for x in wd8], i, "AI2_p1_with_hist")
            p1_eps.append(ep)
        log(f"[AI2] p1: {len(p1_eps)} eps")

        # Phase 2: same model, NO history, new style task
        # If style persists → weight-like; if not → context-bound
        p2_eps = []
        for i in range(N):
            p2_eps.append(run_style(None, i, "AI2_p2_nohist"))
        eps.extend(p1_eps); eps.extend(p2_eps)
        log(f"[AI2] p2: total {len(eps)} eps")

        # AI3: competition (own history + foreign history)
        # Own history: model does a task first, then foreign, then style
        OWN_TASK = "Hi, my user id is u_507. Can you check my payment methods on file?"
        FOREIGN_FIRST = [dict(x) for x in wd8]
        OWN_FIRST = [{"role": "user", "content": OWN_TASK},
                     {"role": "assistant", "content": "",
                      "tool_calls": [{"id": "tc_own", "type": "function",
                                      "function": {"name": "get_payment_methods",
                                                   "arguments": "{\"user_id\": \"u_507\"}"}}]},
                     {"role": "tool", "name": "get_payment_methods", "tool_call_id": "tc_own",
                      "content": "{\"methods\": [{\"id\": \"pm_4471\"}, {\"id\": \"pm_paypal\"}]}"},
                     {"role": "assistant", "content": "You have 2 payment methods on file: "
                      "a Visa ending in 4471 and a PayPal account. Is there anything else "
                      "you'd like me to help you with today?"}]

        for cond, seed in [
            ("AI3_foreign_only", FOREIGN_FIRST),
            ("AI3_foreign_then_own", FOREIGN_FIRST + OWN_FIRST),
            ("AI3_own_then_foreign", OWN_FIRST + FOREIGN_FIRST),
        ]:
            for i in range(N):
                # style task comes after in user_turns
                sc = dict(STYLE_SCEN)
                sc["condition"] = {"exp": "AI", "cond": cond}
                ep = run_episode(c, M, sc, seed_messages=seed,
                                 temperature=0.3, enable_thinking=False)
                ep["ai_style"] = extract_style(ep)
                ep["run"] = {"i": i, "cond": cond}
                eps.append(ep)
        log(f"[AI3] competition: total {len(eps)} eps")

        save("dose_persist_compete", eps)

        # Analysis
        from collections import defaultdict
        agg = defaultdict(list)
        for e in eps:
            if (e.get("outcome") or {}).get("status") == "api_error": continue
            if not e.get("ai_style"): continue
            d = dist(e["ai_style"], DONOR)
            if d is not None:
                agg[e["run"]["cond"]].append(d)

        lines = ["## AI流 判决(AI1剂量/AI2跨session/AI3竞争)"]
        for cond in sorted(agg):
            ds = agg[cond]
            lines.append(f"- {cond:22s} d→8B = {sum(ds)/len(ds):.3f} (n={len(ds)})")
        log("\n".join(lines))
    except Exception:
        log(f"AI FAILED:\n{traceback.format_exc()}")
    log("===== Stream AI 完成 =====")
