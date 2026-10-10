"""Send one recorded request. Every call lands in traces/<exp>.jsonl.

Examples:
  python3 -I tools/req.py E1 GET /
  python3 -I tools/req.py E1 POST /items --json '{"name":"a"}'
  python3 -I tools/req.py E1 GET /items --auth none
  python3 -I tools/req.py E1 GET /items --auth wrong -H 'X-Test: 1'
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hb import Recorder, Request, Target  # noqa: E402

AUTH_MODES = ("ok", "none", "wrong", "lower", "noscheme", "empty", "basic")


def auth_headers(mode: str, token: str) -> list[tuple[str, str]]:
    return {
        "ok": [("Authorization", f"Bearer {token}")],
        "none": [],
        "wrong": [("Authorization", "Bearer not-the-token")],
        "lower": [("Authorization", f"bearer {token}")],
        "noscheme": [("Authorization", token)],
        "empty": [("Authorization", "Bearer ")],
        "basic": [("Authorization", f"Basic {token}")],
    }[mode]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("exp")
    p.add_argument("method")
    p.add_argument("path")
    p.add_argument("--target", default="original", choices=["original", "replica"])
    p.add_argument("--auth", default="ok", choices=AUTH_MODES)
    p.add_argument("-H", "--header", action="append", default=[])
    p.add_argument("--json", help="JSON body (sets Content-Type: application/json)")
    p.add_argument("--data", help="raw body, no Content-Type added")
    p.add_argument("--note", default="")
    p.add_argument("--quiet", action="store_true", help="print status line only")
    a = p.parse_args()

    target = Target.from_env(a.target)
    headers = auth_headers(a.auth, target.token)
    body = b""
    if a.json is not None:
        headers.append(("Content-Type", "application/json"))
        body = a.json.encode()
    elif a.data is not None:
        body = a.data.encode()
    for h in a.header:
        k, _, v = h.partition(":")
        headers.append((k.strip(), v.strip()))

    rec = Recorder(a.exp, target)
    res = rec(Request(a.method, a.path, headers, body), note=a.note)

    print(f"{res.status} {res.reason}  ({res.elapsed_ms} ms)")
    if not a.quiet:
        for k, v in res.headers:
            print(f"{k}: {v}")
        print()
        print(res.body.decode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
