"""Find the accepted control value for a message prefix by sweeping 0..99.

A response other than E202 ("control inválido") means the control was accepted.
Rate-limited to stay under the 10 req/s per-token limit.

  python3 tools/sweep.py E2 "CONSULTA;A" "CONSULTA;B"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hb import Recorder, Target  # noqa: E402
from seq import msg  # noqa: E402


def sweep(rec: Recorder, prefix: str, lo: int = 0, hi: int = 99, rps: float = 8.0):
    for c in range(lo, hi + 1):
        started = time.monotonic()
        res = msg(rec, {"m": f"{prefix};{c}"}, note=f"sweep control for {prefix!r}: try {c}")
        if any(k.lower() == "x-frontier-infra" for k, _ in res.headers):
            raise SystemExit("rate-limited by infra; stopping")
        body = json.loads(res.body)
        if not (isinstance(body, dict) and body.get("error") == "E202"):
            return c, res.status, body
        time.sleep(max(0.0, 1 / rps - (time.monotonic() - started)))
    return None, None, None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("exp")
    p.add_argument("prefixes", nargs="+")
    a = p.parse_args()
    rec = Recorder(a.exp, Target.from_env("original"))
    for prefix in a.prefixes:
        c, status, body = sweep(rec, prefix)
        print(f"{prefix!r:<32} control={c}  -> {status} {json.dumps(body, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
