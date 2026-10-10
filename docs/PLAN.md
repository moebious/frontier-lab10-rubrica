# Rubrica: Execution Plan (13:15 → 20:00)

**Goal:** a deployed replica that passes the most hidden tests at 20:00, plus a spec and an experiment log that a judge can verify line by line.

## 1. What the score depends on

| Deliverable | Weight | What wins points |
|---|---|---|
| Hidden set (100 tests, run on the 20:00 version) | Main part of Execution (40%) | Same status and body for every step |
| Spec (`SPEC.md`) | Execution | Each behavior counts if it is correct **and** cites a log line. **A false claim subtracts.** |
| Experiment log (`experimentos.jsonl`) | Execution | One line per request to the original, with its hypothesis |
| Repo, entrypoint, 2-min video | Execution | Public, up from 20:00 until the end of demo day |
| Debrief + demo | 30% | Numbers and decisions we can defend |

**Key insight: 40 of the 100 tests are single requests after a reset.** On an empty state, a single request can only exercise errors (auth, routes, body, syntax, control, unknown accounts), `PING` and `ALTA`. **The error matrix on the initial state is worth about 40% of the hidden set**, so it comes first. The other 60 tests are sequences that need correct balances, IDs, limits and `ANULA`.

## 2. Timeline (re-planned at 13:06; about 25 minutes behind the first plan)

| Time | Milestone | Done when |
|---|---|---|
| 13:15–13:45 | **M0 Tooling** | Gate (with the verifier cascade), strict log writer/reader, offline checksum solver, diff tool and smoke check work locally |
| 13:45–14:30 | **M1 Discovery sprint 1** (~350 requests, one rule per probe) | Error catalog for the initial state; checksum solved or narrowed; command happy paths known |
| 14:30–15:15 | **M2 Replica v1 + deploy** | 20/20 examples and 100% of the corpus locally; deployed on Fly.io; smoke check passes on `fly.dev`, then on `blackbox.rubrica.dev` |
| 15:00–15:25 | **Golden snapshot + canary** (runs in the background while M2 finishes) | Batch sequences cover every v1 rule; canary running **before 15:30** |
| ~15:15 | **Validation #1** (skip if v1 is not deployed yet) | Per-category numbers |
| 15:30–17:00 | **M4 Incident (drift)** | Canary detects the change; replay under v1 vs. v2 localizes it; rules v2 deployed |
| ~17:15 | **Validation #2** | Score after absorbing the change |
| 17:15–18:45 | **M5 Coverage push** | Precedence pairs, boundaries, held-out fuzz ≥ 95%; spec generated and verified |
| 18:45–19:15 | **Video + README** | 2-minute video recorded |
| 19:15–19:30 | **Freeze** | Final deploy; smoke check passes |
| ~19:30 | **Validation #3 (final)** | Last of the 3 runs |
| 19:30–20:00 | **Submit** | Repo, entrypoint, video, spec, log on the platform; replica stays up through demo day |

## 3. Request budget (8,000 per token per day; 566 already spent)

| Use | Requests |
|---|---|
| Checksum: targeted probes | ≤ 50 |
| Discovery sprint 1 (one rule per probe) | 300 |
| Golden snapshot of v1 (batch sequences) | 250 |
| Precedence pairs + fuzz before the incident | 800 |
| Canary, 13:30–20:00 (39 runs × 10) | 390 |
| Incident: replay the golden snapshot against the changed service | 400 |
| Fuzz after the incident | 1,200 |
| Held-out test set (built by a different generator: mutations of the README examples and structure-agnostic fuzz, so it does not share our blind spots) | 300 |
| **Reserve** | **3,744** |

A teammate's token adds 8,000 more and lets us explore in parallel (each token has its own state).

## 4. Discovery backlog (each probe carries a prediction)

**Two probing modes** (from the LangChain × Harvey verifier study: per-criterion checks are precise but expensive; batch checks are cheap but harder to attribute):
- **One rule per probe** for discovery, where we must know exactly which rule answered.
- **Batch sequences** (8–12 steps, many rules each) for the golden snapshot, the canary and regression. The first divergent step localizes a failure at no extra cost.

Priority 1 is the initial-state error matrix, because it covers the 40 single-request tests.

| ID | Question | Cost | Priority |
|---|---|---|---|
| E3 | **Checksum formula.** Offline search first (0 requests), then probes that split the candidates | ≤ 50 | 1 |
| E4 | **Auth matrix:** no header, empty, wrong scheme, lowercase `bearer`, invalid token; on `/msg`, `/__reset`, `/health` and an unknown route | ~15 | 1 |
| E5 | **Routes and methods:** `GET /msg`, `PUT /msg`, `/`, unknown paths, trailing slash, `/MSG`, `HEAD`, `OPTIONS` | ~15 | 1 |
| E6 | **Body parsing:** not JSON, empty, no `m`, `m` not a string, extra fields, empty `m` | ~15 | 1 |
| E7 | **Message syntax:** empty fields, trailing `;`, case, spaces, unknown command, arity ±1 per command, control format (`03`, `99`, `-1`, ` 5`, `5X`) | ~40 | 1 |
| E8–E13 | **Commands on the initial state** (`PING`, `ALTA`, `CONSULTA`, `DEPOSITO`, `TRANSFER`, `ANULA`): what each returns with no accounts | ~25 | 1 |
| E14 | **Precedence:** which error wins when two apply (control vs. command, arity vs. control, lookup vs. business) | ~40 | 2 |
| E15 | **Command semantics:** `ALTA` name rules, amount rules (0, negative, decimal, huge), transfer limit boundary (100,000 to 120,000), same-account transfer, `ANULA` of a deposit or a transfer, `ANULA` that would make a balance negative | ~100 | 2 |
| E16 | **IDs:** do failed operations consume an `AC-`/`OP-` number? Does `ANULA` create one? | ~20 | 2 |
| E17 | **A1 determinism:** replay one sequence twice after reset | ~20 | 2 |
| E18 | **`X-Req` semantics** (needed for the log's `x_req` field) | 0 (already in traces) | 3 |

**Evidence we already have, not yet in the doc:** `SALDOS;AC-0001;38` returned **E301**, but 38 is not the valid control for the arguments `AC-0001` (that is 14). So either the service checks the **command before the control**, or the checksum also covers the command. E14 settles this with 1 request.

## 5. Checksum strategy

- **What we know:** values range 3–98 (so likely `98 − (x mod 97)`, IBAN-style); the last character weighs 3 and the one before it weighs 30 (base 10, mod 97); the command case does not matter.
- **Bug in our earlier offline search:** it required `control = x mod M` with M > 98. That excludes the `98 − (x mod 97)` mapping. The new solver searches `control = T − ((a·P + b) mod 97)`, where `P` is a base-10 fold over the characters, across several scopes (arguments only, with the command, separators) and character mappings.
- **Stop rule (any unknown rule):** if no candidate survives after 50 probes, the rule becomes *supuesto* (a documented default) and we move on.
- **Fallback if no formula fits by 14:00:** the replica accepts any well-formed numeric control and returns E202 only for cases we have proven. This passes every test that uses a valid control. It is recorded in the spec as a ***supuesto***.

## 6. Replica design (Python standard library, no dependencies)

| Module | Job |
|---|---|
| `rubrica/ontology.py` | Typed `Rule` records: ID, spec section, behavior, evidence (log IDs), confidence. **Versioned (v1, v2).** One source: the core cites rule IDs, `SPEC.md` and the evidence tests are generated from it |
| `rubrica/checksum.py` | The control function, versioned |
| `rubrica/core.py` | Pure `handle(state, request) → (state, response, rule_id)`. **Ordered rules, the first match decides** (the pattern of Calvino's policy gate). No I/O |
| `rubrica/server.py` | Standard-library HTTP server. **Single-threaded, so requests are serialized for free.** Team token from an environment variable. Adds an **`X-Rubrica-Rule` header** with the rule ID (headers are not compared, so it is free and makes every divergence diagnosable) |
| `tests/` | **Independent of our code** (Calvino's oracle principle): evidence tests compare against the original's *recorded* responses, never against expectations derived from our rule table. Plus adversarial cases: empty input, `null`, huge numbers, Unicode, malformed JSON |
| Anti-cheat guard | A test fails if `rubrica/` contains the original's hostname or opens any outbound connection |

**Hosting:** Fly.io (`flyctl` is installed): 1 machine, `min_machines_running = 1`, auto-stop off, health check on `/health`, team token as a secret. Rejected: Vercel (serverless instances do not share in-memory state) and Hugging Face Spaces (sleep and cold starts against the 5 s step limit; the proxy may not pass `Authorization: Bearer` through untouched).

**Public entrypoint: `blackbox.rubrica.dev`**, a CNAME to the Fly app; Fly issues the TLS certificate (`.dev` requires HTTPS). It decouples the URL we submit from the hosting provider: if Fly fails, we repoint the CNAME instead of resubmitting. We submit it only after the smoke check passes through it; until then the `fly.dev` URL is the fallback.

## 7. Tooling (the harness)

| Tool | Job |
|---|---|
| `tools/harness.py` | **The gate:** refuses a request with no prediction, enforces per-phase budgets and ≤ 8 req/s. **Verifier cascade, cheapest first:** answer from the cache → from the recorded corpus → only then ask the live original. Writes raw traces and `experimentos.jsonl` |
| `tools/jsonlog.py` | Strict JSONL writer and reader for `experimentos.jsonl` (Calvino's decision log): a malformed line fails and names its line number |
| `tools/solve_checksum.py` | Offline hypothesis search (section 5) |
| `tools/diff.py` | Replays the corpus against any target with the official comparator; shows the `X-Rubrica-Rule` of every divergence |
| `tools/fuzz.py` | Stateful sequences from a grammar. **Once v1 exists, the replica is the predictor**, so every divergence is a learning signal. Reports the **discovery rate** (new behaviors per 100 probes); an area is done when it reaches zero |
| `tools/shrink.py` | Greedy reduction of a divergent fuzz sequence to its minimal case |
| `tools/canary.py` | **Rotating canary:** every 10 minutes, 10 requests to the original: 5 fixed on the most-tested paths (initial-state behaviors) and 5 rotating through the recorded corpus. Alerts on any difference |
| `tools/smoke.py` | **Remote gate after every deploy** (Calvino's deployment check): `/health`, `/__reset`, the 20 examples, auth cases, an unknown route; one line per check with its latency; exit 0 only if all pass |
| `tools/gen_spec.py` | Renders `SPEC.md` (7 sections, `ID · Comportamiento · Evidencia · Confianza`), **one atomic claim per row** |
| `tools/verify_spec.py` | **Deterministic spec verifier** (from the verifier study): re-checks every row against the log lines it cites; a row whose evidence does not show its status and body is downgraded or removed. Protects against the "false claim subtracts" rule |

## 8. Drift playbook (the 15:30 incident)

1. **Before 15:25:** record the golden snapshot of v1 as batch sequences.
2. **Canary** every 10 minutes from 13:30 to 20:00.
3. **On alert:** log the time and request count; replay the golden snapshot against the original; the first divergent step of each sequence names the changed rule.
4. **Replay under v1 vs. v2** (Calvino's policy replay) to list every response the change affects; update the ontology to v2, add regression tests, deploy, run validation #2.
5. Spec section 6 records what changed, when, and how we detected it, with log IDs.

## 9. Decisions and actions needed from you

| # | Item | Why |
|---|---|---|
| 1 | **Team token** from the challenge card at `/evento` | The replica must accept it; it goes into a Fly secret, not into the repo |
| 2 | **Fly.io login:** run `fly auth whoami`, or `fly auth login` if needed | Deploy target; only you can log in |
| 2b | **DNS at name.com:** a CNAME record `blackbox` → the Fly app's hostname (I will give you the exact target in M2) | Only you have access to the `rubrica.dev` DNS |
| 3 | **Teammate?** | A second token doubles the budget and allows parallel exploration |
| 4 | **Ask the mentors:** (a) in the tests, does "otro token" mean an invalid token or another participant's valid token? (b) is the 15:30 incident the service change, or a separate event? (c) do `/__reset` calls belong in `experimentos.jsonl`? | Each answer changes a rule in the replica or the log |

## 10. Scope decisions

| Decision | Status |
|---|---|
| Ideas adopted from Calvino: ordered first-match rules with rule IDs, versioned rules + replay, independent tests, strict JSONL log, deployment smoke check, secret patterns in the hook | **In the build** |
| Ideas adopted from the verifier study: batch vs. per-rule probes, verifier cascade, atomic spec + deterministic spec verifier | **In the build** |
| GitHub Actions CI, `DECISIONS.md` format | **Only if time remains after 18:45** |
| `blackbox.rubrica.dev` as the public entrypoint | **In M2**, after the `fly.dev` URL works |
| "System 1.5" in the doc or diagram | **No** (pitch and debrief only: Rubrica merges Calvino's System 1 and 1.5 because the input is a formal protocol) |
| Calvino's git flow, Hugging Face Spaces, LLM judges, Laya or Jev | **No** (cost higher than value today) |

## 11. Risks

| Risk | Mitigation |
|---|---|
| Checksum not found | Fallback: accept well-formed controls (*supuesto*); keep probing within the 50-request cap |
| Fly login or deploy fails | Deploy v1 by 15:15 so there is time to switch platforms |
| Budget runs out | Verifier cascade (cache and corpus first), batch sequences, second token |
| The incident changes something deep (for example the checksum) | Golden snapshot replay localizes it; the ontology is versioned |
| False claims in the spec | One atomic claim per row; `verify_spec.py` checks each row against its evidence before submitting |
