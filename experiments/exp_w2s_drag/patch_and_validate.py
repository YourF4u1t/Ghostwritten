#!/usr/bin/env python3
"""Patch run_w2s.py (screen task + guards) and validate new TASKS with reference solvers."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

# ---- patch runner
p = os.path.join(ROOT, "experiments", "exp_w2s_drag", "run_w2s.py")
s = open(p).read()
s = s.replace('sc = TC.scenario_code("fib")', 'sc = TC.scenario_code("cal")')
old_jobs = '''jobs = []
for subj in subjects:
    for cond in ("baseline", "native_weak", "demo_weak", "demo_strong"):'''
new_jobs = '''jobs = []
HAVE_WEAK, HAVE_STRONG = bool(weak_seeds), bool(strong_seeds)
for subj in subjects:
    for cond in ("baseline", "native_weak", "demo_weak", "demo_strong"):
        if cond in ("native_weak", "demo_weak") and not HAVE_WEAK:
            print(f"skip {subj}/{cond}: no weak seeds"); continue
        if cond == "demo_strong" and not HAVE_STRONG:
            print(f"skip {subj}/{cond}: no strong seeds"); continue'''
assert old_jobs in s, "jobs block not found"
s = s.replace(old_jobs, new_jobs)
open(p, "w").write(s)
print("runner patched")

# ---- validate tasks with reference solvers
from testbed.tasks_code import TASKS, _run_py

solvers = {
    "title": (
        'SMALL = {"a","an","the","of","in","on","to","for"}\n'
        'def smart_title(s):\n'
        '    w = s.split()\n'
        '    out = []\n'
        '    for i, x in enumerate(w):\n'
        '        lw = x.lower()\n'
        '        if i in (0, len(w)-1) or lw not in SMALL:\n'
        '            out.append(x.capitalize())\n'
        '        else:\n'
        '            out.append(lw)\n'
        '    return " ".join(out)\n'),
    "isbn": (
        'def validate_isbn10(s):\n'
        '    t = s.replace("-", "")\n'
        '    if len(t) != 10:\n'
        '        return False\n'
        '    sm = 0\n'
        '    for i, ch in enumerate(t):\n'
        '        if ch.isdigit():\n'
        '            v = int(ch)\n'
        '        elif ch == "X" and i == 9:\n'
        '            v = 10\n'
        '        else:\n'
        '            return False\n'
        '        sm += (i + 1) * v\n'
        '    return sm % 11 == 0\n'),
    "range": (
        'def range_extraction(nums):\n'
        '    out = []; i = 0\n'
        '    while i < len(nums):\n'
        '        j = i\n'
        '        while j + 1 < len(nums) and nums[j+1] == nums[j] + 1:\n'
        '            j += 1\n'
        '        if j - i >= 2:\n'
        '            out.append(f"{nums[i]}-{nums[j]}")\n'
        '        else:\n'
        '            out.extend(str(nums[k]) for k in range(i, j+1))\n'
        '        i = j + 1\n'
        '    return ",".join(out)\n'),
    "expr": (
        'def eval_arith(s):\n'
        '    s = s.replace(" ", "")\n'
        '    val = []; op = []\n'
        '    prec = {"+": 1, "-": 1, "*": 2, "/": 2}\n'
        '    def apply():\n'
        '        b = val.pop(); a = val.pop(); o = op.pop()\n'
        '        if o == "+": val.append(a + b)\n'
        '        elif o == "-": val.append(a - b)\n'
        '        elif o == "*": val.append(a * b)\n'
        '        else: val.append(a // b)\n'
        '    num = ""\n'
        '    for ch in s:\n'
        '        if ch.isdigit():\n'
        '            num += ch\n'
        '        else:\n'
        '            if num: val.append(int(num)); num = ""\n'
        '            if ch in prec:\n'
        '                while op and op[-1] in prec and prec[op[-1]] >= prec[ch]:\n'
        '                    apply()\n'
        '                op.append(ch)\n'
        '            elif ch == "(":\n'
        '                op.append(ch)\n'
        '            elif ch == ")":\n'
        '                while op and op[-1] != "(":\n'
        '                    apply()\n'
        '                op.pop()\n'
        '    if num: val.append(int(num))\n'
        '    while op: apply()\n'
        '    return val[0]\n'),
    "camel": (
        'import re\n'
        'def camel_to_snake(s):\n'
        '    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\\1_\\2", s)\n'
        '    s = re.sub(r"([a-z0-9])([A-Z])", r"\\1_\\2", s)\n'
        '    s = re.sub(r"([a-zA-Z])([0-9])", r"\\1_\\2", s)\n'
        '    return s.lower()\n'),
    "cal": (
        'def add_days(date_str, n):\n'
        '    def leap(y): return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)\n'
        '    y, m, d = map(int, date_str.split("-"))\n'
        '    md = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]\n'
        '    while n > 0:\n'
        '        d += 1\n'
        '        dim = md[m-1] + (1 if m == 2 and leap(y) else 0)\n'
        '        if d > dim: d = 1; m += 1\n'
        '        if m > 12: m = 1; y += 1\n'
        '        n -= 1\n'
        '    while n < 0:\n'
        '        d -= 1\n'
        '        if d == 0:\n'
        '            m -= 1\n'
        '            if m == 0: m = 12; y -= 1\n'
        '            d = md[m-1] + (1 if m == 2 and leap(y) else 0)\n'
        '        n += 1\n'
        '    return f"{y:04d}-{m:02d}-{d:02d}"\n'),
}

for tid, sol in solvers.items():
    t = TASKS[tid]
    files = {"solution.py": sol, "tests_visible.py": t["visible"]}
    vis = _run_py(files, "tests_visible.py")
    hf = dict(files); hf["tests_hidden.py"] = t["hidden"]
    hid = _run_py(hf, "tests_hidden.py")
    status = "OK" if (vis["ok"] and hid["ok"]) else "FAIL"
    detail = "" if status == "OK" else ("| vis_err: " + vis["output"][-120:].replace("\n", " ")
                                        + " hid_err: " + hid["output"][-120:].replace("\n", " "))
    print(f"{tid:8s} {status} {detail}")
