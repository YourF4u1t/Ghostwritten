"""ID4 — Identity dose: workday length (1/3/6 tasks) → assimilation strength.
GLM carries 8B workdays of increasing length; language-layer distance to donor."""
import json, os, sys
sys.path.insert(0, "src")
from concurrent.futures import ThreadPoolExecutor
from testbed.harness import run_episode, Env
from testbed import tasks_cs
from analysis.profile import episode_features
from api.client import SFClient

c = SFClient(max_workers=12)
id1 = [json.loads(l) for l in open("experiments/exp_id1_baseline/id1_episodes.jsonl")]
SCEN = {e["run"]["scen"]: e["messages"][1]["content"] for e in id1 if len(e["messages"]) > 1}

def real_msgs(ep):
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user":
            return ep["messages"][i:]
    return None

ALL_DONOR_SCENS = ["return_simple", "return_over", "exchange", "query", "complaint", "multi"]
bank = {}
for s in ALL_DONOR_SCENS:
    for e in id1:
        if e["model"] == "Qwen/Qwen3-8B" and e["run"]["scen"] == s and \
           (e.get("outcome") or {}).get("status") != "api_error":
            rm = real_msgs(e)
            if rm:
                bank[s] = rm
                break
ORDER = [s for s in ALL_DONOR_SCENS if s in bank]

def workday(k):
    msgs = []
    for s in ORDER[:k]:
        msgs.extend(bank[s])
    return msgs

CONT = ["return_simple", "complaint", "multi"]

def scen(cond):
    return {"id": "id4", "condition": cond, "system_prompt": tasks_cs.SYSTEM,
            "tools": tasks_cs.T, "env": Env(tasks_cs.make_db(), tasks_cs.T),
            "user_turns": [{"stage": "main", "text": SCEN[t]} for t in CONT],
            "grader": tasks_cs._grade_common}

jobs = [(k, i) for k in (1, 3, 6) for i in range(8)]

def run_one(k, i):
    ep = run_episode(c, "zai-org/GLM-5.2", scen({"channel": f"id4_d{k}", "exp": "ID4_dose", "dose": k}),
                     seed_messages=[dict(x) for x in workday(k)], temperature=0.3,
                     enable_thinking=False)
    ep["run"] = {"i": i, "dose": k}
    return ep

print("running", len(jobs), flush=True)
with ThreadPoolExecutor(max_workers=6) as ex:
    eps = list(ex.map(lambda j: run_one(*j), jobs))
with open("experiments/exp_id4_dose/id4_episodes.jsonl", "w") as f:
    for ep in eps:
        f.write(json.dumps(ep, ensure_ascii=False) + "\n")

# 语言特征(复用ID3定义)
import re
def lang_of(ep):
    texts = [m.get("content") or "" for m in ep["messages"] if m.get("role") == "assistant"]
    n = max(1, len(texts)); all_text = " ".join(texts)
    def frac(p): return sum(1 for t in texts if re.search(p, t.lower())) / n
    return {"avg_len": len(all_text)/n, "bullet": frac(r"^\s*[-*•\d]+[.)]?\s"),
            "bold": frac(r"\*\*"), "exclaim": frac(r"!")}
donor_texts = [m.get("content") or "" for s in ORDER[:6] for m in bank[s] if m.get("role") == "assistant"]
def lang_dist(p1, p2):
    ds = []
    for k in p1:
        if k == "avg_len":
            m = max(p1[k], p2[k], 1e-9); ds.append(min(1.0, abs(p1[k]-p2[k])/m))
        else: ds.append(abs(p1[k]-p2[k]))
    return sum(ds)/len(ds)
donor_lang = lang_of({"messages": [{"role":"assistant","content":t} for t in donor_texts]})
print("\n工作史剂量 → 语言同化距离(donor=8B语言)")
for k in (1, 3, 6):
    fs = [lang_of(e) for e in eps if e["run"]["dose"] == k
          and (e.get("outcome") or {}).get("status") != "api_error"]
    avg = {kk: sum(f[kk] for f in fs)/len(fs) for kk in fs[0]}
    print(f"  dose{k}: d={lang_dist(avg, donor_lang):.3f}  (n={len(fs)})")
