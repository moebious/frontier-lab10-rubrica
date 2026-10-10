"""Run a recorded sequence: POST /__reset, then each message in order via POST /msg.

Input: a JSONL file whose lines have {"request": {...}} and optionally
{"status": int, "response": ...} (expected values, compared with the official rule:
same status, JSON-equal body with key order ignored, otherwise exact text).

  python3 tools/seq.py E1 material/pruebas/ejemplos.jsonl --hyp "examples replay"
  python3 tools/seq.py E2 my_seq.jsonl --target replica
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hb import Recorder, Request, Response, Target, auth  # noqa: E402


def body_equal(expected, actual_bytes: bytes) -> bool:
    try:
        actual = json.loads(actual_bytes)
    except ValueError:
        return isinstance(expected, str) and expected == actual_bytes.decode("utf-8", "replace")
    return expected == actual  # dict equality ignores key order; lists keep order


def msg(rec: Recorder, payload, note: str = "") -> Response:
    body = json.dumps(payload, ensure_ascii=False).encode()
    headers = auth(rec.target.token) + [("Content-Type", "application/json")]
    return rec(Request("POST", "/msg", headers, body), note=note)


def reset(rec: Recorder) -> Response:
    rec.new_sequence()
    return rec(Request("POST", "/__reset", auth(rec.target.token)), note="__reset")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("exp")
    p.add_argument("file")
    p.add_argument("--target", default="original", choices=["original", "replica"])
    p.add_argument("--hyp", default="")
    a = p.parse_args()

    rec = Recorder(a.exp, Target.from_env(a.target))
    steps = [json.loads(line) for line in Path(a.file).read_text().splitlines() if line.strip()]
    reset(rec)
    mismatches = 0
    for i, step in enumerate(steps, 1):
        res = msg(rec, step["request"], note=step.get("hipotesis", a.hyp))
        shown = res.body.decode("utf-8", "replace")
        verdict = ""
        if "status" in step:
            ok = res.status == step["status"] and body_equal(step["response"], res.body)
            mismatches += not ok
            verdict = "  OK" if ok else f"  MISMATCH expected {step['status']} {json.dumps(step['response'], ensure_ascii=False)}"
        xreq = next((v for k, v in res.headers if k.lower() == "x-req"), "-")
        print(f"{i:>2} x-req={xreq:<4} {res.status} {json.dumps(step['request'], ensure_ascii=False)} -> {shown}{verdict}")
    if any("status" in s for s in steps):
        print(f"\n{len(steps) - mismatches}/{len(steps)} match")


if __name__ == "__main__":
    main()
