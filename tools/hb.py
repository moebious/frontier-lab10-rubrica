"""Black-box HTTP harness core: byte-exact requests, every exchange recorded to JSONL.

Uses http.client directly so nothing is added to the request that we did not ask for
(no automatic Accept-Encoding, User-Agent, or Content-Type). Host and Content-Length
are added only when the caller does not pass them explicitly, and can be suppressed.
"""

from __future__ import annotations

import base64
import http.client
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
TRACES = ROOT / "traces"

Headers = list[tuple[str, str]]


def load_env(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Target:
    name: str
    base_url: str
    token: str

    @classmethod
    def from_env(cls, name: str) -> "Target":
        load_env()
        prefix = name.upper()
        url = os.environ.get(f"{prefix}_URL")
        if not url:
            raise SystemExit(f"{prefix}_URL is not set (see .env.example)")
        return cls(name, url.rstrip("/"), os.environ.get(f"{prefix}_TOKEN", ""))


@dataclass
class Request:
    method: str
    path: str
    headers: Headers = field(default_factory=list)
    body: bytes = b""
    auto_host: bool = True
    auto_content_length: bool = True


@dataclass
class Response:
    status: int
    reason: str
    headers: Headers
    body: bytes
    elapsed_ms: float


def _has(headers: Headers, name: str) -> bool:
    return any(k.lower() == name.lower() for k, _ in headers)


def send(target: Target, req: Request, timeout: float = 15.0) -> Response:
    parts = urlsplit(target.base_url)
    conn_cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(parts.hostname, parts.port, timeout=timeout)
    path = (parts.path.rstrip("/") + req.path) if req.path.startswith("/") else req.path
    try:
        started = time.perf_counter()
        conn.putrequest(req.method, path or "/", skip_host=True, skip_accept_encoding=True)
        if req.auto_host and not _has(req.headers, "Host"):
            conn.putheader("Host", parts.netloc)
        for key, value in req.headers:
            conn.putheader(key, value)
        if req.auto_content_length and req.body and not _has(req.headers, "Content-Length"):
            conn.putheader("Content-Length", str(len(req.body)))
        conn.endheaders(req.body or None)
        raw = conn.getresponse()
        body = raw.read()
        elapsed = (time.perf_counter() - started) * 1000
        return Response(raw.status, raw.reason, list(raw.getheaders()), body, round(elapsed, 1))
    finally:
        conn.close()


def auth(token: str, scheme: str = "Bearer") -> Headers:
    return [("Authorization", f"{scheme} {token}")]


def _body_fields(body: bytes) -> dict:
    out: dict = {"body_b64": base64.b64encode(body).decode()}
    try:
        out["body_text"] = body.decode("utf-8")
    except UnicodeDecodeError:
        out["body_text"] = None
    return out


def _redact(headers: Headers, secrets: list[str]) -> list[list[str]]:
    redacted = []
    for k, v in headers:
        for s in secrets:
            if s:
                v = v.replace(s, "<TOKEN>")
        redacted.append([k, v])
    return redacted


class Recorder:
    """Appends every exchange of one experiment to traces/<exp>.jsonl."""

    def __init__(self, experiment: str, target: Target):
        TRACES.mkdir(exist_ok=True)
        self.experiment = experiment
        self.target = target
        self.path = TRACES / f"{experiment}.jsonl"
        self.step = 0
        self.sequence = 0

    def new_sequence(self) -> None:
        self.sequence += 1
        self.step = 0

    def __call__(self, req: Request, note: str = "") -> Response:
        res = send(self.target, req)
        secrets = [self.target.token]
        record = {
            "exp": self.experiment,
            "seq": self.sequence,
            "step": self.step,
            "ts": datetime.now(timezone.utc).isoformat(),
            "target": self.target.name,
            "note": note,
            "req": {
                "method": req.method,
                "path": req.path,
                "headers": _redact(req.headers, secrets),
                **_body_fields(req.body),
            },
            "res": {
                "status": res.status,
                "reason": res.reason,
                "headers": [list(h) for h in res.headers],
                **_body_fields(res.body),
                "elapsed_ms": res.elapsed_ms,
            },
        }
        with self.path.open("a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.step += 1
        return res
