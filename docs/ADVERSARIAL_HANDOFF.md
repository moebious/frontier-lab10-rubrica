# Adversarial Review Handoff: Design Doc (Reto 2 · La caja negra)

**Deadline:** the design doc must be final before **12:00 Bogotá time**. Report within **8 minutes**. Report only issues that can be fixed in under 5 minutes, or issues that are false claims.

## Your task
Audit `docs/DESIGN.pdf` (source: `docs/DESIGN.md`) as a strict senior judge. Score it with the rubric below. Find:
1. **False or unsupported claims** (highest priority; false claims cost points).
2. **Gaps that keep a criterion below a 4.**
3. **Internal contradictions** (numbers, orders, names).
4. **Sentences that break ASD-STE100 Simplified Technical English** without a technical reason: more than 25 words, passive voice, more than one idea per sentence, idioms.

Do not suggest new features or more scope. The doc must stay **one page**.

## Files to read
| File | Why |
|---|---|
| `docs/DESIGN.md` | The doc under review (the PDF is rendered from it) |
| `material/README.md` | The official challenge brief: protocol, scoring, rules, spec and log formats |
| `material/pruebas/ejemplos.jsonl` | 20 official request/response examples |
| `site/diagram.png` | The architecture diagram (a second deliverable; check that it agrees with the doc) |
| `traces/E1.jsonl`, `traces/E2.jsonl` | Our real experiments so far (tokens redacted) |

## Rubric (Systems Design, 30% of the total)
| Criterion | What judges look for | Score 1 | Score 4 |
|---|---|---|---|
| Problem understanding | What the system must solve, its limits and assumptions | Repeats the brief, no decisions | Names assumptions, hard cases and what it leaves out, with reasons |
| Architecture and trade-offs | Clear components, justified decisions | A diagram with no decisions behind it | Each decision says which alternative it rejected and why |
| Plan to measure | How the team knows it works, before building | No way to measure the result | Concrete test cases and metrics from the design |

## Verified facts (use these to check claims)
- **E1:** replaying the 20 official examples gave **20/20 matches** against the live service. `X-Req` is a per-token request counter since reset.
- **E2:** a blind sweep of controls 0–99 cost **543 requests**. Accepted controls: `CONSULTA;A→98`, `;B→95`, `;C→92`, `;AA→95`, `;AB→92`, `;BA→65`. All other values returned `E202`.
- A missing account with a wrong control returns **E202**, not E401. So the service checks the control before the account lookup.
- From the examples: `CONSULTa;AC-0001;14` and `CONSULTA;AC-0001;14` are both accepted (same control, so the command is case-insensitive or not part of the checksum). `AC-0001→14`, `AC-0002→11`, `AC-0009→87`.
- **Not yet verified:** the exact checksum formula. Simple linear positional hashes (bases 10/16/31/…, moduli 97–999) fit offline did **not** match all points. Treat any claim about the exact formula as a hypothesis.
- Budget used so far: about **565 of 8,000** requests on this token.

## Claims we already know are weak (confirm or refute)
1. **A3:** "mod-97 family checksum on the arguments only, with an IBAN-style transform (`98 − x`)". Is "probable" justified by the facts above, or is it an overclaim?
2. **"About log₂(H) requests, approximately 10–15":** is that a reasonable estimate or unsupported?
3. **Canary budget:** "10-request canary every 10 min (~500/day)". Check the arithmetic for 12:00–20:00.
4. **Budget plan:** 2,000 + 2,500 + 500 + 3,000 = 8,000. Is it consistent with 565 already spent?
5. **Decision-core order:** route → auth → parse → control → command → arity → lookup → business rule → effect. Which steps does the evidence support, and which are guesses that should be marked as such?
6. **"Code gate (`beforeToolCall` hook)":** it does not exist in code yet. Is the doc honest that it is a design, not a built feature?

## Required output format
Return **at most 10 findings**, most severe first:

```
[SEVERITY: false-claim | below-4 | contradiction | STE]
Where: <section and quote, max 15 words>
Problem: <one sentence>
Fix: <exact replacement text, one-page safe>
```

Then give one line with a score per criterion (1–4) and one line: **SUBMIT AS IS** or **FIX FIRST**.
