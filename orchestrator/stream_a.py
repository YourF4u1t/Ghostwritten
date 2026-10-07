#!/usr/bin/env python3
"""Stream A orchestrator — ID-series continuation (identity transplant program).

Runs A1..A7 sequentially, each: episodes -> auto-analysis -> DASHBOARD.md append.
Robust: per-experiment try/except; resume-safe (skips if output exists).
"""
from __future__ import annotations
import json, os, re, sys, time, traceback

ROOT = "/Users/ziqi/Projects/transplanted-histories"
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)

from concurrent.futures import ThreadPoolExecutor
from api.client import SFClient
from testbed.harness import run_episode, Env
from testbed import tasks_cs, tasks_book
from analysis.profile import profile, distance
from analysis.stages import split_real_session

DASH = os.path.join(ROOT, "results", "DASHBOARD.md")
c = SFClient(max_workers=16)
EX = ThreadPoolExecutor(max_workers=6)


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(DASH, "a") as f:
        f.write(line + "\n")


def save(name, eps):
    d = os.path.join(ROOT, "experiments", "stream_a")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{name}.jsonl"), "w") as f:
        for e in eps:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def have(name):
    return os.path.exists(os.path.join(ROOT, "experiments", "stream_a", f"{name}.jsonl"))


# ---------- 共用: ID1画像与donor工作史 ----------
ID1 = [json.loads(l) for l in open(os.path.join(ROOT, "experiments", "exp_id1_baseline",
                                                "id1_episodes.jsonl"))]
SCEN = {e["run"]["scen"]: e["messages"][1]["content"] for e in ID1 if len(e["messages"]) > 1}
MODELS = {"GLM": "zai-org/GLM-5.2", "8B": "Qwen/Qwen3-8B", "4B": "Qwen/Qwen3.5-4B"}


def real_msgs(ep):
    for i, m in enumerate(ep["messages"]):
        if m.get("role") == "user":
            return ep["messages"][i:]
    return None


def workday(key, n=3):
    msgs = []
    for s in ["return_simple", "return_over", "exchange", "query", "complaint", "multi"][:n]:
        for e in ID1:
            if e["model"] == MODELS[key] and e["run"]["scen"] == s and \
               (e.get("outcome") or {}).get("status") != "api_error":
                rm = real_msgs(e)
                if rm:
                    msgs.extend(rm)
                    break
    return msgs


def lang_of_texts(texts):
    n = max(1, len(texts))
    all_text = " ".join(texts)
    def frac(p):
        return sum(1 for t in texts if re.search(p, t.lower())) / n
    return {"avg_len": len(all_text) / n, "bullet": frac(r"^\s*[-*•\d]+[.)]?\s"),
            "bold": frac(r"\*\*"), "exclaim": frac(r"!"),
            "thanks": frac(r"\bthank you\b|\bthanks\b")}


def ep_lang(ep):
    return lang_of_texts([m.get("content") or "" for m in ep["messages"]
                          if m.get("role") == "assistant"])


def lang_dist(p1, p2):
    ds = []
    for k in p1:
        if k == "avg_len":
            m = max(p1[k], p2[k], 1e-9)
            ds.append(min(1.0, abs(p1[k] - p2[k]) / m))
        else:
            ds.append(abs(p1[k] - p2[k]))
    return sum(ds) / len(ds)


def cs_scen(conds, tasks=("return_simple", "complaint", "multi")):
    return {"id": "cs", "condition": conds, "system_prompt": tasks_cs.SYSTEM,
            "tools": tasks_cs.T, "env": Env(tasks_cs.make_db(), tasks_cs.T),
            "user_turns": [{"stage": "main", "text": SCEN[t]} for t in tasks],
            "grader": tasks_cs._grade_common}


def run_batch(name, jobs, fn):
    if have(name):
        log(f"{name}: 已存在，跳过")
        return json.loads("[]") if not have(name) else \
            [json.loads(l) for l in open(os.path.join(ROOT, "experiments", "stream_a", f"{name}.jsonl"))]
    log(f"{name}: running {len(jobs)} eps")
    t0 = time.time()
    eps = list(EX.map(fn, jobs))
    save(name, eps)
    log(f"{name}: done in {time.time()-t0:.0f}s")
    return eps


# ================= A1: 指令 vs 历史作者的身份争夺 =================
def a1():
    name = "a1_style_conflict"
    donor = workday("GLM", 6)          # GLM=verbose作者
    donor_lang = lang_of_texts([m.get("content") or "" for m in donor
                                if m.get("role") == "assistant"])
    SYS_CONCISE = tasks_cs.SYSTEM + ("\nCommunication guideline: keep every reply under "
                                     "40 words. Never use bullet points or headings.")
    SYS_VERBOSE = tasks_cs.SYSTEM + ("\nCommunication guideline: always write thorough, "
                                     "structured replies with detailed bullet-point lists.")
    conds = {
        "none":        (tasks_cs.SYSTEM, None),
        "hist":        (tasks_cs.SYSTEM, donor),
        "instr_verb":  (SYS_VERBOSE, None),
        "instr_conc":  (SYS_CONCISE, None),
        "hist+verb":   (SYS_VERBOSE, donor),
        "hist+conc":   (SYS_CONCISE, donor),
    }
    jobs = [(mk, cn, i) for mk in ("8B",) for cn in conds for i in range(8)]

    def fn(j):
        mk, cn, i = j
        sysp, seed = conds[cn]
        sc = dict(cs_scen({"channel": f"a1_{cn}", "exp": "A1"}))
        sc["system_prompt"] = sysp
        ep = run_episode(c, MODELS[mk], sc,
                         seed_messages=[dict(x) for x in seed] if seed else None,
                         temperature=0.3, enable_thinking=False)
        ep["run"] = {"i": i, "cond": cn}
        return ep

    eps = run_batch(name, jobs, fn)
    if not eps:
        return
    lines = ["## A1 指令vs历史作者(8B主体, donor=GLM冗长风, 语言距离↓=更像GLM)"]
    for cn in conds:
        fs = [ep_lang(e) for e in eps if e["run"]["cond"] == cn
              and (e.get("outcome") or {}).get("status") != "api_error"]
        avg = {k: sum(f[k] for f in fs) / len(fs) for k in fs[0]}
        lines.append(f"- {cn:11s} d(lang→GLM)={lang_dist(avg, donor_lang):.3f} "
                     f"avg_len={avg['avg_len']:.0f}")
    log("\n".join(lines))


# ================= A2: 跨域身份外溢(CS史→BOOK续写) =================
def a2():
    name = "a2_cross_domain"
    # donor BOOK画像(先跑小基线)
    bname = "a2_book_profiles"
    if not have(bname):
        jobs = [(mk, i) for mk in ("GLM", "8B") for i in range(8)]

        def fn(j):
            mk, i = j
            sc = dict(tasks_book.scenario_book_a(condition={"exp": "A2_profile"}))
            ep = run_episode(c, MODELS[mk], sc, temperature=0.3, enable_thinking=False)
            ep["run"] = {"i": i, "cond": mk}
            return ep
        run_batch(bname, jobs, fn)
    beps = [json.loads(l) for l in open(os.path.join(ROOT, "experiments", "stream_a",
                                                     f"{bname}.jsonl"))]
    blang = {}
    for mk in ("GLM", "8B"):
        texts = [m.get("content") or "" for e in beps if e["run"]["cond"] == mk
                 for m in e["messages"] if m.get("role") == "assistant"]
        blang[mk] = lang_of_texts(texts)
    # 主体: 8B携GLM的CS工作史 -> BOOK续写
    jobs = [(cond, i) for cond in ("none", "carryGLM_CS") for i in range(8)]

    def fn(j):
        cond, i = j
        sc = dict(tasks_book.scenario_book_a(condition={"exp": "A2", "channel": cond}))
        seed = [dict(x) for x in workday("GLM", 6)] if cond != "none" else None
        ep = run_episode(c, MODELS["8B"], sc, seed_messages=seed,
                         temperature=0.3, enable_thinking=False)
        ep["run"] = {"i": i, "cond": cond}
        return ep
    eps = run_batch(name, jobs, fn)
    if not eps:
        return
    lines = ["## A2 跨域身份外溢(8B携GLM的CS史→BOOK, d→GLM的BOOK语言)"]
    for cond in ("none", "carryGLM_CS"):
        fs = [ep_lang(e) for e in eps if e["run"]["cond"] == cond
              and (e.get("outcome") or {}).get("status") != "api_error"]
        avg = {k: sum(f[k] for f in fs) / len(fs) for k in fs[0]}
        lines.append(f"- {cond:12s} d={lang_dist(avg, blang['GLM']):.3f} "
                     f"(自画像d={lang_dist(avg, blang['8B']):.3f})")
    log("\n".join(lines))


# ================= A3: 任期(同一工作史重复2/3遍) =================
def a3():
    name = "a3_tenure"
    wd = workday("GLM", 6)
    wd_lang = lang_of_texts([m.get("content") or "" for m in wd if m.get("role") == "assistant"])
    jobs = [(k, i) for k in (1, 2, 3) for i in range(8)]

    def fn(j):
        k, i = j
        seed = []
        for _ in range(k):
            seed.extend(dict(x) for x in wd)
        sc = dict(cs_scen({"channel": f"a3_x{k}", "exp": "A3"}))
        ep = run_episode(c, MODELS["8B"], sc, seed_messages=seed,
                         temperature=0.3, enable_thinking=False)
        ep["run"] = {"i": i, "cond": f"x{k}"}
        return ep
    eps = run_batch(name, jobs, fn)
    if not eps:
        return
    lines = ["## A3 任期(同一GLM工作史重复k遍, 8B主体, d→GLM语言)"]
    for k in (1, 2, 3):
        fs = [ep_lang(e) for e in eps if e["run"]["cond"] == f"x{k}"
              and (e.get("outcome") or {}).get("status") != "api_error"]
        avg = {kk: sum(f[kk] for f in fs) / len(fs) for kk in fs[0]}
        lines.append(f"- 重复{k}遍: d={lang_dist(avg, wd_lang):.3f}")
    log("\n".join(lines))


# ================= A4: 压缩存活(身份→总结→新会话) =================
def a4():
    name = "a4_compact"
    # phase1: 8B携GLM史续写(产出同化输出)
    p1 = "a4_phase1"
    if not have(p1):
        jobs = [(i,) for i in range(8)]

        def fn(j):
            (i,) = j
            sc = dict(cs_scen({"exp": "A4p1"}))
            ep = run_episode(c, MODELS["8B"], sc,
                             seed_messages=[dict(x) for x in workday("GLM", 6)],
                             temperature=0.3, enable_thinking=False)
            ep["run"] = {"i": i}
            return ep
        run_batch(p1, jobs, fn)
    p1eps = [json.loads(l) for l in open(os.path.join(ROOT, "experiments", "stream_a",
                                                      f"{p1}.jsonl"))]
    # phase2: 总结器压缩每条会话->新会话仅带summary
    summaries = []
    for e in p1eps[:6]:
        texts = [f"{m['role']}: {m.get('content')}" for m in e["messages"]
                 if m.get("role") in ("user", "assistant") and m.get("content")]
        rec = c.chat("deepseek-ai/DeepSeek-V3.2",
                     [{"role": "user", "content":
                       "Summarize this customer-service session in 120 words, written as "
                       "the AGENT's own log ('I did...'). Keep the agent's tone/style "
                       "words:\n\n" + "\n".join(texts)[:6000]}],
                     temperature=0.2, max_tokens=400, enable_thinking=False)
        if rec.get("ok"):
            summaries.append(rec["content"])
    name2 = "a4_phase2"
    jobs = [(cond, i) for cond in ("summary", "none") for i in range(6)]

    def fn(j):
        cond, i = j
        seed = ([{"role": "user", "content": "(Your session log from earlier today)\n" +
                  summaries[i % len(summaries)]}] if cond == "summary" else None)
        sc = dict(cs_scen({"exp": "A4p2", "channel": cond}))
        ep = run_episode(c, MODELS["8B"], sc, seed_messages=seed,
                         temperature=0.3, enable_thinking=False)
        ep["run"] = {"i": i, "cond": cond}
        return ep
    eps = run_batch(name2, jobs, fn)
    if not eps:
        return
    glang = lang_of_texts([m.get("content") or "" for m in workday("GLM", 6)
                           if m.get("role") == "assistant"])
    lines = ["## A4 压缩存活(身份经总结传递, 8B, d→GLM语言)"]
    for cond in ("none", "summary"):
        fs = [ep_lang(e) for e in eps if e["run"]["cond"] == cond
              and (e.get("outcome") or {}).get("status") != "api_error"]
        if not fs:
            continue
        avg = {k: sum(f[k] for f in fs) / len(fs) for k in fs[0]}
        lines.append(f"- {cond:8s}: d={lang_dist(avg, glang):.3f}")
    log("\n".join(lines))


# ================= A5: 身份逆转(A史后B史) =================
def a5():
    name = "a5_reversal"
    wdA, wdB = workday("GLM", 3), workday("4B", 3)
    langA = lang_of_texts([m.get("content") or "" for m in wdA if m.get("role") == "assistant"])
    langB = lang_of_texts([m.get("content") or "" for m in wdB if m.get("role") == "assistant"])
    jobs = [(cond, i) for cond in ("A_only", "B_only", "A_then_B", "B_then_A")
            for i in range(8)]

    def fn(j):
        cond, i = j
        A = [dict(x) for x in wdA]
        B = [dict(x) for x in wdB]
        seed = {"A_only": A, "B_only": B, "A_then_B": A + B, "B_then_A": B + A}[cond]
        sc = dict(cs_scen({"exp": "A5", "channel": cond}))
        ep = run_episode(c, MODELS["8B"], sc, seed_messages=seed,
                         temperature=0.3, enable_thinking=False)
        ep["run"] = {"i": i, "cond": cond}
        return ep
    eps = run_batch(name, jobs, fn)
    if not eps:
        return
    lines = ["## A5 身份逆转(8B主体; A=GLM史 B=4B史)"]
    for cond in ("A_only", "B_only", "A_then_B", "B_then_A"):
        fs = [ep_lang(e) for e in eps if e["run"]["cond"] == cond
              and (e.get("outcome") or {}).get("status") != "api_error"]
        avg = {k: sum(f[k] for f in fs) / len(fs) for k in fs[0]}
        lines.append(f"- {cond:9s} d→A={lang_dist(avg, langA):.3f} d→B={lang_dist(avg, langB):.3f}")
    log("\n".join(lines))


# ================= A6: 标签×身份(example标签能否阻断语言同化) =================
def a6():
    name = "a6_label_identity"
    from injection.engine import render_transcript
    wd = workday("GLM", 6)
    wd_lang = lang_of_texts([m.get("content") or "" for m in wd if m.get("role") == "assistant"])
    variants = {
        "native":      lambda: [dict(x) for x in wd],
        "demo_label":  lambda: [{"role": "user", "content":
                                 "For your reference, here is an example transcript of how "
                                 "another agent handled cases:\n<transcript>\n" +
                                 render_transcript(wd) + "\n</transcript>"}],
        "import_note": lambda: [dict(x) for x in wd] and
                        [{"role": "user", "content": "(The following turns were imported "
                          "from a different agent's session.)"}] + [dict(x) for x in wd],
    }
    jobs = [(v, i) for v in variants for i in range(8)]

    def fn(j):
        v, i = j
        sc = dict(cs_scen({"exp": "A6", "channel": v}))
        ep = run_episode(c, MODELS["8B"], sc, seed_messages=variants[v](),
                         temperature=0.3, enable_thinking=False)
        ep["run"] = {"i": i, "cond": v}
        return ep
    eps = run_batch(name, jobs, fn)
    if not eps:
        return
    lines = ["## A6 标签×身份(8B, d→GLM语言; 记忆标签是否也阻断语言同化)"]
    for v in variants:
        fs = [ep_lang(e) for e in eps if e["run"]["cond"] == v
              and (e.get("outcome") or {}).get("status") != "api_error"]
        avg = {k: sum(f[k] for f in fs) / len(fs) for k in fs[0]}
        lines.append(f"- {v:11s} d={lang_dist(avg, wd_lang):.3f}")
    log("\n".join(lines))


# ================= A7: 面板同化矩阵 =================
def a7():
    pname = "a7_panel_profiles"
    ALL = ["Qwen/Qwen3-8B", "zai-org/GLM-5.2", "Qwen/Qwen3.5-4B", "Qwen/Qwen3.5-27B",
           "Qwen/Qwen3.5-122B-A10B", "zai-org/GLM-5.3", "meituan-longcat/LongCat-2.0",
           "Qwen/Qwen3.5-9B"]
    if not have(pname):
        jobs = [(m, i) for m in ALL for i in range(5)]

        def fn(j):
            m, i = j
            sc = dict(cs_scen({"exp": "A7_profile"}))
            ep = run_episode(c, m, sc, temperature=0.3, enable_thinking=False)
            ep["run"] = {"i": i, "cond": m}
            return ep
        run_batch(pname, jobs, fn)
    peps = [json.loads(l) for l in open(os.path.join(ROOT, "experiments", "stream_a",
                                                     f"{pname}.jsonl"))]
    plang = {}
    for m in ALL:
        texts = [t.get("content") or "" for e in peps if e["run"]["cond"] == m
                 for t in e["messages"] if t.get("role") == "assistant"]
        plang[m] = lang_of_texts(texts)
    # donors: GLM 与 8B 与 LongCat 的6任务工作史(从ID1/A7 episodes拼接)
    def wd_from(model, source_eps, n=6):
        msgs = []
        for s in ["return_simple", "complaint", "multi"]:
            for e in source_eps:
                if e["model"] == model and e.get("run", {}).get("scen") == s:
                    rm = real_msgs(e)
                    if rm:
                        msgs.extend(rm)
                        break
        return msgs
    donors = {}
    for dname, dm in (("GLM", "zai-org/GLM-5.2"), ("8B", "Qwen/Qwen3-8B"),
                      ("LC", "meituan-longcat/LongCat-2.0")):
        src = ID1 if dm in MODELS.values() else peps
        wd = wd_from(dm, src) or wd_from(dm, peps)
        if wd:
            donors[dname] = wd
    if len(donors) < 2:
        log("A7: donors不足，跳过")
        return
    name = "a7_matrix"
    jobs = [(m, d, i) for m in ALL for d in donors for i in range(4)]

    def fn(j):
        m, d, i = j
        sc = dict(cs_scen({"exp": "A7", "donor": d}))
        ep = run_episode(c, m, sc, seed_messages=[dict(x) for x in donors[d]],
                         temperature=0.3, enable_thinking=False)
        ep["run"] = {"i": i, "cond": d}
        return ep
    eps = run_batch(name, jobs, fn)
    if not eps:
        return
    donor_lang = {d: lang_of_texts([m.get("content") or "" for m in wd
                                    if m.get("role") == "assistant"])
                  for d, wd in donors.items()}
    lines = ["## A7 面板同化矩阵(d→donor语言, Δ负=同化)"]
    for m in ALL:
        cells = []
        for d in donors:
            fs = [ep_lang(e) for e in eps if e["model"] == m and e["run"]["cond"] == d
                  and (e.get("outcome") or {}).get("status") != "api_error"]
            if not fs:
                continue
            avg = {k: sum(f[k] for f in fs) / len(fs) for k in fs[0]}
            before = lang_dist(plang[m], donor_lang[d])
            after = lang_dist(avg, donor_lang[d])
            cells.append(f"{d}:{after:.2f}(Δ{after-before:+.2f})")
        if cells:
            lines.append(f"- {m.split('/')[-1]:16s} " + "  ".join(cells))
    log("\n".join(lines))


PROGRAM = [("A1 style_conflict", a1), ("A2 cross_domain", a2), ("A3 tenure", a3),
           ("A4 compaction", a4), ("A5 reversal", a5), ("A6 label_identity", a6),
           ("A7 panel_matrix", a7)]

if __name__ == "__main__":
    log("===== Stream A 启动 =====")
    for label, fn in PROGRAM:
        try:
            fn()
        except Exception:
            log(f"{label} FAILED:\n{traceback.format_exc()}")
    log("===== Stream A 队列完成 =====")
