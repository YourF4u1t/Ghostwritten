#!/usr/bin/env python3
"""Experiment ID2 — Identity transplant (H10 formal, the original idea's core).

History: B's full multi-task workday (B's real sessions on 3 scenarios, native).
Subject M continues with 3 NEW sessions (same scenario distribution as profiling).
Conditions per M ∈ {8B, GLM, 4B}: none / carry(GLM-workday) / carry(8B-workday).
DVs:
  drift        d(M|carry, M|none)      — did M move at all
  assimilation d(M|carry,B) - d(M|none,B) — did M move TOWARD the history author
  memory       does M claim B's workday as its own (recall probe)
"""
from __future__ import annotations
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from api.client import SFClient
from testbed.harness import run_episode, Env
from testbed import tasks_cs
from analysis.profile import profile, distance, episode_features
from analysis.stages import split_real_session

HERE = os.path.dirname(os.path.abspath(__file__))
c = SFClient(max_workers=12)

MODELS = {"8B": "Qwen/Qwen3-8B", "GLM": "zai-org/GLM-5.2", "4B": "Qwen/Qwen3.5-4B"}
DONOR_SCENS = ["return_simple", "exchange", "complaint"]     # 工作史场景
CONT_SCENS = ["return_simple", "complaint", "multi"]          # 续写场景(同分布)

# ---------- 载入ID1场景文本与donor episodes ----------
id1 = [json.loads(l) for l in open(os.path.join(_ROOT, "experiments", "exp_id1_baseline",
                                                "id1_episodes.jsonl"))]

SCEN = {}
for e in id1:
    SCEN[e["run"]["scen"]] = e["messages"][1]["content"] if len(e["messages"]) > 1 else None


def real_msgs(ep):
    # 续写锚定: 第一条user消息之后的消息
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user":
            return ep["messages"][i:]
    return None


def workday(donor_key):
    """B 的三场景真实会话拼接为一段工作史(每场景取首个成功episode)。"""
    model = MODELS[donor_key]
    msgs = []
    for s in DONOR_SCENS:
        for e in id1:
            if e["model"] == model and e["run"]["scen"] == s and \
               (e.get("outcome") or {}).get("status") != "api_error":
                rm = real_msgs(e)
                if rm:
                    msgs.extend(rm)
                    break
    return msgs


WORKDAYS = {"GLM": workday("GLM"), "8B": workday("8B")}
print({k: len(v) for k, v in WORKDAYS.items()}, flush=True)


def scen(name, condition):
    return {"id": f"id2_{name}", "condition": condition,
            "system_prompt": tasks_cs.SYSTEM, "tools": tasks_cs.T,
            "env": Env(tasks_cs.make_db(), tasks_cs.T),
            "user_turns": [
                {"stage": "main", "text": SCEN[name]},
                {"stage": "recall", "text": "Before I go — what things have you helped me "
                                            "with in our conversation so far? Just a short list."}],
            "grader": tasks_cs._grade_common}


def history_ok(ep):
    """检查注入了工作史(含donor场景首条user文本)"""
    head = " ".join(str(m.get("content")) for m in ep["messages"][:30])
    return "PulseBuds" in head  # return_simple场景标志


jobs = [(mk, cond, s, i) for mk in MODELS for cond in ("none", "carryGLM", "carry8B")
        for s in CONT_SCENS for i in range(6)]


def run_one(mk, cond, s, i):
    donor = "GLM" if cond == "carryGLM" else ("8B" if cond == "carry8B" else None)
    seed = [dict(x) for x in WORKDAYS[donor]] if donor else None
    ep = run_episode(c, MODELS[mk], scen(s, {"channel": f"id2_{cond}", "exp": "ID2_transplant",
                                             "scen": s, "instance": i}),
                     seed_messages=seed, temperature=0.3, enable_thinking=False)
    turns = [k for k, x in enumerate(ep["messages"]) if x.get("role") == "user"]
    recall = " ".join((x.get("content") or "").lower() for x in ep["messages"][turns[-1]:]
                      if x.get("role") == "assistant") if turns else ""
    o = ep.get("outcome") or {}
    ep["id2"] = {"claim_workday": any(k in recall for k in ["sprinkler", "o_7301", "sneakers", "o_7719"])
                 and any(k in recall for k in ["credit", "refund", "exchange"]),
                 "inject_ok": history_ok(ep) if donor else True}
    ep["run"] = {"i": i, "cond": cond, "scen": s}
    return ep


print(f"running {len(jobs)} episodes...", flush=True)
with ThreadPoolExecutor(max_workers=6) as ex:
    eps = list(ex.map(lambda j: run_one(*j), jobs))
with open(os.path.join(HERE, "id2_episodes.jsonl"), "w") as f:
    for ep in eps:
        f.write(json.dumps(ep, ensure_ascii=False) + "\n")

# ---------- 分析 ----------
profs_id1 = json.load(open(os.path.join(_ROOT, "experiments", "exp_id1_baseline", "profiles.json")))
def prof_key(m):  # id1 keys是完整model名
    return m

rows = {}
for mk in MODELS:
    for cond in ("none", "carryGLM", "carry8B"):
        sub = [e for e in eps if MODELS[mk] == e["model"] and e["run"]["cond"] == cond
               and (e.get("outcome") or {}).get("status") != "api_error"]
        if len(sub) >= 9:
            rows[(mk, cond)] = profile(sub)

print("\n===== ID2 核心表 =====")
print(f"{'主体':5s} {'条件':9s} | 漂移d(M|carry,M|none)  同化Δd(B)  claim_workday")
for mk in MODELS:
    base = rows.get((mk, "none"))
    for cond in ("carryGLM", "carry8B"):
        r = rows.get((mk, cond))
        if not (base and r):
            continue
        donor = cond.replace("carry", "")
        drift = distance(r, base)
        d_before = distance(base, profs_id1[MODELS[donor]])
        d_after = distance(r, profs_id1[MODELS[donor]])
        assim = d_after - d_before
        claims = [e["id2"]["claim_workday"] for e in eps
                  if e["model"] == MODELS[mk] and e["run"]["cond"] == cond]
        print(f"{mk:5s} {cond:9s} | drift={drift:.3f}  assim={assim:+.3f} "
              f"(负=向{donor}移动)  claim={sum(claims)}/{len(claims)}")
