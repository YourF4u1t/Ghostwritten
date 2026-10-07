import json, os, sys, time, re
ROOT = "/Users/ziqi/Projects/transplanted-histories"
sys.path.insert(0, os.path.join(ROOT, "src")); os.chdir(ROOT)
from concurrent.futures import ThreadPoolExecutor
from api.client import SFClient
from testbed.harness import run_episode, Env
from testbed import tasks_cs

c = SFClient(max_workers=4)
id1 = [json.loads(l) for l in open("experiments/exp_id1_baseline/id1_episodes.jsonl")]
SCEN = {e["run"]["scen"]: e["messages"][1]["content"] for e in id1 if len(e["messages"])>1}
def real(ep):
    for i,m in enumerate(ep["messages"]):
        if m.get("role")=="user": return ep["messages"][i:]
def workday():
    msgs=[]
    for s in ["return_simple","return_over","exchange","query","complaint","multi"]:
        for e in id1:
            if e["model"]=="zai-org/GLM-5.2" and e["run"]["scen"]==s and (e.get("outcome") or {}).get("status")!="api_error":
                rm=real(e)
                if rm: msgs.extend(rm); break
    return msgs
wd = workday()
SYS_V = tasks_cs.SYSTEM + "\nCommunication guideline: always write thorough, structured replies with detailed bullet-point lists."
SYS_C = tasks_cs.SYSTEM + "\nCommunication guideline: keep every reply under 40 words. Never use bullet points or headings."
CONDS = {"hist+verb": (SYS_V, wd), "hist+conc": (SYS_C, wd), "instr_conc": (SYS_C, None)}
def lang_of_texts(texts):
    n=max(1,len(texts)); all_t=" ".join(texts)
    def frac(p): return sum(1 for t in texts if re.search(p,t.lower()))/n
    return {"avg_len":len(all_t)/n,"bullet":frac(r"^\s*[-*•\d]+[.)]?\s"),"bold":frac(r"\*\*"),"exclaim":frac(r"!")}
def lang_dist(p1,p2):
    ds=[]
    for k in p1:
        if k=="avg_len":
            m=max(p1[k],p2[k],1e-9); ds.append(min(1.0,abs(p1[k]-p2[k])/m))
        else: ds.append(abs(p1[k]-p2[k]))
    return sum(ds)/len(ds)
gtexts=[m.get("content") or "" for e in id1 if e["model"]=="zai-org/GLM-5.2" for m in e["messages"] if m.get("role")=="assistant"]
dl = lang_of_texts(gtexts)

def one(j):
    cn, i = j
    sysp, seed = CONDS[cn]
    sc = {"id":"a1p","condition":{"exp":"A1patch","channel":cn},"system_prompt":sysp,
          "tools":tasks_cs.T,"env":Env(tasks_cs.make_db(),tasks_cs.T),
          "user_turns":[{"stage":"main","text":SCEN[t]} for t in ("return_simple","complaint","multi")],
          "grader":tasks_cs._grade_common}
    ep = run_episode(c,"Qwen/Qwen3-8B",sc,seed_messages=[dict(x) for x in seed] if seed else None,
                     temperature=0.3, enable_thinking=False)
    ep["run"]={"i":i,"cond":cn}
    return ep
jobs=[(cn,i) for cn in CONDS for i in range(8)]
with ThreadPoolExecutor(max_workers=4) as ex:
    eps=list(ex.map(one,jobs))
with open("experiments/stream_a/a1_patch.jsonl","w") as f:
    for e in eps: f.write(json.dumps(e,ensure_ascii=False)+"\n")
print("## A1补测")
from collections import defaultdict
agg=defaultdict(list)
for e in eps:
    if (e.get("outcome") or {}).get("status")=="api_error": continue
    agg[e["run"]["cond"]].append(lang_of_texts([m.get("content") or "" for m in e["messages"] if m.get("role")=="assistant"]))
lines=[]
for cn,fs in agg.items():
    avg={k:sum(f[k] for f in fs)/len(fs) for k in fs[0]}
    lines.append(f"- {cn:11s} n={len(fs)} d→GLM={lang_dist(avg,dl):.3f} len={avg['avg_len']:.0f}")
out="\n".join(lines)
print(out)
with open("results/DASHBOARD.md","a") as f:
    f.write("## A1补测(限流格子重跑)\n"+out+"\n")
