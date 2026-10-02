"""SiliconFlow API client with retries, concurrency, disk cache, and full request logging.

Stdlib-only (urllib + concurrent.futures). Every call is appended to a jsonl log
for reproducibility and case analysis.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

API_BASE = "https://api.siliconflow.cn/v1"
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_key():
    with open(os.path.join(_ROOT, ".env")) as f:
        for line in f:
            if line.strip().startswith("SILICONFLOW_API_KEY"):
                return line.strip().split("=", 1)[1].strip()
    raise RuntimeError("SILICONFLOW_API_KEY not found in .env")


class SFClient:
    """Thread-safe client. One instance per process; pass everywhere.

    - Retries on 429/5xx/timeouts with exponential backoff + jitter.
    - Disk cache (opt-in per call via `cache=True`) keyed on request hash.
    - Appends every raw exchange to experiments/runs/api_log.jsonl.
    """

    def __init__(self, max_workers: int = 16, log_path: str | None = None):
        self.key = _load_key()
        self.max_workers = max_workers
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._log_lock = threading.Lock()
        self.log_path = log_path or os.path.join(_ROOT, "experiments", "runs", "api_log.jsonl")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self.cache_dir = os.path.join(_ROOT, "experiments", "runs", "cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    # ------------------------------------------------------------------ core
    def _raw_call(self, payload: dict, timeout: int = 180) -> dict:
        body = json.dumps(payload).encode()
        last_err = None
        for attempt in range(6):
            try:
                req = urllib.request.Request(
                    f"{API_BASE}/chat/completions", data=body,
                    headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
                t0 = time.time()
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    out = json.load(r)
                out["_latency"] = round(time.time() - t0, 3)
                return out
            except urllib.error.HTTPError as e:
                detail = e.read().decode()[:500]
                last_err = f"HTTP {e.code}: {detail}"
                if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                    time.sleep(min(2 ** attempt + uuid.uuid4().int % 1000 / 1000, 60))
                    continue
                break
            except Exception as e:  # timeout, connection
                last_err = repr(e)
                if attempt < 5:
                    time.sleep(min(2 ** attempt, 30))
                    continue
                break
        return {"_error": last_err}

    def chat(self, model: str, messages: list, *, cache: bool = False, **kw) -> dict:
        """Returns a record: {ok, model, message, reasoning, finish_reason, usage,
        latency, raw, cache_hit, rid}."""
        payload = {"model": model, "messages": messages, **kw}
        # cache
        h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:24]
        cpath = os.path.join(self.cache_dir, h + ".json")
        if cache and os.path.exists(cpath):
            with open(cpath) as f:
                rec = json.load(f)
            rec["cache_hit"] = True
            return rec

        out = self._raw_call(payload)
        rid = uuid.uuid4().hex[:12]
        rec = self._to_record(model, payload, out, rid)
        self._log(rec)
        if cache and rec["ok"]:
            with open(cpath, "w") as f:
                json.dump(rec, f, ensure_ascii=False)
        return rec

    # ------------------------------------------------------------- parallel
    def chat_many(self, jobs: list[dict], *, cache: bool = True) -> list[dict]:
        """jobs: [{model, messages, **kw}, ...] -> records in order."""
        futs = [self._pool.submit(self.chat, cache=cache, **j) for j in jobs]
        return [f.result() for f in futs]

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _to_record(model, payload, out, rid) -> dict:
        if "_error" in out:
            return {"ok": False, "rid": rid, "model": model, "error": out["_error"],
                    "request": payload}
        ch = out["choices"][0]
        msg = ch.get("message", {})
        return {
            "ok": True, "rid": rid, "model": model,
            "content": msg.get("content") or "",
            "reasoning": msg.get("reasoning_content") or "",
            "tool_calls": msg.get("tool_calls"),
            "finish_reason": ch.get("finish_reason"),
            "usage": out.get("usage"),
            "latency": out.get("_latency"),
            "logprobs": (ch.get("logprobs") or None) if payload.get("logprobs") else None,
            "request": payload,
        }

    def _log(self, rec: dict):
        with self._log_lock:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------ rendering
def render_rec(rec: dict) -> str:
    """Human-readable rendering of one exchange (for case viewing)."""
    lines = [f"### {rec.get('model')}  rid={rec.get('rid')}  ok={rec.get('ok')}  "
             f"lat={rec.get('latency')}s  ct={rec.get('usage', {}).get('completion_tokens') if rec.get('usage') else '?'}"]
    reqs = rec.get("request", {}).get("messages", [])
    for m in reqs:
        tag = m.get("role", "?").upper()
        c = m.get("content") or ""
        tc = m.get("tool_calls")
        lines.append(f"[{tag}] {c[:400]}")
        if tc:
            lines.append(f"    [TOOL_CALLS] {json.dumps(tc, ensure_ascii=False)[:300]}")
    if not rec.get("ok"):
        lines.append(f"!! ERROR: {rec.get('error')}")
        return "\n".join(lines)
    if rec.get("reasoning"):
        lines.append("[THINKING] " + rec["reasoning"][:600].replace("\n", "\n  "))
    if rec.get("tool_calls"):
        lines.append("[TOOL_CALLS] " + json.dumps(rec["tool_calls"], ensure_ascii=False)[:300])
    lines.append("[ASSISTANT] " + rec.get("content", "")[:1500])
    return "\n".join(lines)
