# Design Candidates

Ideas under exploration for `DESIGN.md`. A candidate moves into the design doc once we decide to adopt it. Each entry is ready to paste.

## C1. Dual-process architecture (System 2 discovers, System 1 executes) · **ADOPTED in DESIGN.md v2**

**Idea:** reasoning is slow and happens offline; the runtime is a fast, compiled, deterministic classifier.

| | System 2 (slow, deliberate) | System 1 (fast, reflexive) |
|---|---|---|
| Where | Offline discovery loop | Deployed replica, hot path |
| What | Human + reasoning LLM read traces, form hypotheses, design experiments to confirm them | Deterministic decision table compiled from *confirmed* hypotheses: auth → route → method → body → validation → state |
| Speed | Minutes per hypothesis | Microseconds per request |
| Can it be wrong? | Yes, so every hypothesis needs an experiment | No: it only executes proven rules |

**Decision row for DESIGN.md:**
| Runtime intelligence | **Dual-process:** reasoning offline (System 2) compiled into a deterministic decision table at runtime (System 1) | *LLM (even a small, fast one) deciding responses at runtime:* not byte-exact, not deterministic across replays after `__reset`, adds latency, cost and a failure mode to the 20:00–23:00 window, and resembles "a tool doing the work for you". |

**Where a fast classifier *does* help, with no LLM involved:**
- **Divergence triage:** sort diff failures into status, header, body, key-order or volatile-field differences.
- **Drift triage:** tell real behavior change from normal variation such as timestamps and IDs.
- **Fallback for unseen requests:** if no rule matches, use the nearest known response class (an unknown route gets the 404 template).

**Pitch line:** *"System 2 discovers, System 1 executes."*

**Search terms on X:** `"System 1" "System 2" LLM` · `"dual process" agents` · `neurosymbolic` · `"LLM to rules" distillation` · `"program synthesis" from examples` · `"LLM as compiler"`

## C3. Agent harness engineering (the discovery loop as an agent harness) · **ADOPTED in DESIGN.md v2**

**Idea:** the System 2 side of C1 is an agent (a reasoning LLM plus the human) running inside a harness we build. The model does not discover the service. **The harness makes its discovery trustworthy:** narrow tools, a ground-truth oracle, persistent memory, guardrails and a stop criterion.

| Harness component | In our design | Why it matters |
|---|---|---|
| **Narrow, typed tools** | `probe` (one recorded request), `sequence` (reset + N steps), `diff` (corpus vs replica), `shrink` (minimal divergence) | The agent cannot send an unrecorded request, so every claim has a trace behind it |
| **Ground-truth oracle (verifiable feedback)** | The original's response *is* the label; `diff` gives an exact pass/fail signal | No LLM-as-judge: the reward signal is exact, so hallucinated rules fail immediately |
| **Persistent memory / context engineering** | `traces/*.jsonl` (raw), `SPEC.md` (distilled rules with trace IDs), coverage matrix (what is left) | The agent works from compact state, not from 10,000 raw exchanges in context |
| **Hypothesis → experiment protocol** | Every rule starts as a hypothesis, is confirmed by a named experiment, then is compiled into the C1 decision table | Produces the experiment-log deliverable as a side effect |
| **Guardrails** | Rate limit on the original, secret redaction in traces, the replica can never reach the original (enforced by an egress check), and no runtime LLM (C1) | Respects both challenge restrictions by construction |
| **Loop control / stop criterion** | Fuzz until new coverage-matrix cells per hour level off, and the canary re-opens the loop when drift appears | "Done" is a measured state, not a feeling |
| **Human checkpoints** | The human approves each hypothesis before it is compiled into the table | Keeps us clearly on the right side of "no tools that do the work for you" |
| **Evals** | The corpus is the eval set, and the hidden-set validations (3) are the held-out test | Same discipline as eval-driven development |

**Decision row for DESIGN.md:**
| Discovery process | **Human-in-the-loop agent harness:** narrow recorded tools + exact oracle + spec as memory + coverage-based stop criterion | *Free-form chat with an LLM about the service:* unverifiable and unreproducible, with no experiment log. *Fully autonomous agent:* hallucinated rules reach the replica, and it violates the spirit of "no tools that do the work for you". *Purely manual curl:* too slow to cover the surface before the behavior change. |

**Pitch line:** *"The model proposes, the harness disposes: every rule in our replica was proposed by reasoning and proven by an experiment against the real service."*

**Search terms on X:** `"agent harness"` · `"harness engineering"` · `"context engineering"` · `"agent scaffolding"` · `"verifiable rewards" agents` · `"eval-driven development"` · `"tool design" agents` · `"human in the loop" agents`

## C4. Service ontology: context as topology (one schema, three jobs) · **ADOPTED in DESIGN.md v2** (lean)

**Idea (adapted from "Context as Topology"):** store what we learn about the black box as **exact structure, not as prose or embeddings**. A typed ontology of the service is the single source of truth, and it does three jobs at once, so they can't drift apart:

| Job | In our design |
|---|---|
| **Index** (what we navigate) | The coverage matrix is the ontology's holes. Unexplored `(route, method, precondition)` cells are exact keys, found by lookup, not similarity search |
| **Mold** (what the agent fills) | A C3 hypothesis is a typed slot: `Rule{route, method, when: [preconditions], then: Outcome{status, error_id, body_template}, evidence: [trace_ids]}`. The agent can't invent structure, only fill fields |
| **Contract** (what everything is checked against) | The same rule table is **executed** by the replica (C1 System 1), **rendered** into `SPEC.md`, and **turned into tests** from its evidence traces |

**The ontology (minimal):**
```
Service ─has→ Resource ─exposed by→ Route(pattern) ─accepts→ Method
Method ─guarded by→ Precondition (ordered: auth → content-type → body shape → field constraint → state)
Precondition ─fails with→ Outcome (status, error_id, body template, headers)
State ─transition(op)→ State        (the topology: the learned state machine)
Rule ─proven by→ Trace (≥1)          (no rule without evidence)
```

**What this changes in practice:**
- **Context projection, not retrieval:** to investigate a divergence, the agent gets only the rule's neighborhood (its route, its ordered preconditions, its evidence traces), not 10,000 raw exchanges.
- **Traces are indexed by exact keys,** `(method, route_pattern, status, precondition_signature)`. There's no vector DB, so there's no false recall.
- **Pre-filled anchors:** observed status codes, headers and error bodies are copied from traces as given. The model only proposes the *conditions* (which precondition, in which order), and every proposal is checked against the oracle before it commits.
- **Drift is a diff between ontology versions:** when the canary fires, the v1 → v2 change shows up as added, removed or changed rules, which makes it easy to explain in the demo.
- **Zero spec/code/test drift:** they are three renderings of the same object.

**Decision row for DESIGN.md:**
| Knowledge representation | **Typed service ontology** (rules with preconditions, outcomes and evidence) as the single source for the replica, the spec and the tests | *Prose spec + hand-written handlers + separate tests:* three copies that drift, especially after the unannounced change. *Embedding/RAG memory over traces:* approximate recall, so it can retrieve the wrong rule with confidence. |

**Keep it lean:** in an 8-hour build the ontology is **just the rule table's schema** (Python dataclasses, or TypeScript + Zod/Effect Schema only if already fluent). No graph database and no ontology tooling. The idea is the asset, not the machinery.

**Verify before citing:** the article cites arXiv:2603.27116 ("The Price of Meaning") and arXiv:2601.19106 (FORGE). Read their abstracts before quoting them in the doc or the debrief.

**Pitch line:** *"Our spec, our replica and our tests are the same object: one typed ontology of the service, rendered three ways."*

**Search terms on X:** `"context as topology"` · `"Effect Schema" annotations` · `"specification mining"` · `"API specification mining"` · `"knowledge graph" vs embeddings agent memory` · `"structured outputs" constrained decoding` · `"ontology" agents` · `"single source of truth" schema` · `"deterministic grounding" LLM`

## C5. Uncertainty-driven exploration (active learning) · **ADOPTED in DESIGN.md v2**

**Idea:** rules are non-deterministic *proposals* until proven. Each rule in the C4 ontology carries a `confidence`: the number of independent supporting traces, reset to zero by any contradicting trace. The fuzzer **targets low-confidence rules and unexplored cells first** instead of exploring uniformly.

**Why:** the same request budget against the original yields more coverage. That matters under rate limits and before the unannounced drift. It also implements the broader thesis: *non-deterministic proposal → deterministic verification → deterministic compilation.*

**Cost:** about 15 lines, a priority sort over fuzz targets by `(confidence, cell_visits)`.

**Pitch / debrief line:** *"We spend experiments where we're least sure."*

**Search terms on X:** `"active learning"` · `"uncertainty sampling"` · `"coverage-guided fuzzing"` · `"decision models" codegen` · `"DMN" decision tables`

## C6. Harness decisions: code when checkable, System One classifier for judgment calls · **ADOPTED in DESIGN.md v2**

Sources: "The Anatomy of an Agent Harness" (Trivedy), "Building a Harness with Jev" (Runkle, Lovell), "Building a Custom Harness with Pi and Jev", "Designing Efficient Verifiers for Legal Agents" (LangChain × Harvey).

**Rule from the Pi + Jev guide:** *anything plain code can check for certain is checked in code.* A probabilistic classifier only gets the judgment calls code can't make. **It never touches the replica's hot path** (C1).

| Harness decision point (System 2 side) | Mechanism | Policy (pure function, thresholds in one place, unit-tested) |
|---|---|---|
| **Gate:** before each probe, is the target allowed and are we under the rate limit? | **Code** (host allowlist, token bucket) | Fail closed: no probe if unsure |
| **Verifier:** is a proposed rule correct? | **Code: replay its evidence traces through the core against the exact oracle** | Accept only on 100% match: zero false passes, zero cost |
| **Drift triage:** is a canary diff real drift or volatile noise (IDs, timestamps, counters)? | Field classifier in code first; a Jev `noul` ("this difference reflects a behavior change") only for unclassified fields | Three verdicts: `≥ blockAt` absorb (open v2), `askAt..blockAt` ask the human, `< askAt` log as volatile. Fail closed: if the classifier is down, treat it as drift and alert |
| **Router:** which model proposes the hypothesis? | Jev `choice` + complexity `score` | Simple single-route rules go to the fast model; precedence and state puzzles go to the powerful one. Pick once per session (prompt caching). Fail open to the powerful model |
| **Decision log** | `decisions.jsonl`: every verdict with its numbers, secrets redacted | Feeds the experiment log and threshold tuning |

**What the legal-verifiers article adds, as a contrast for the debrief:** legal work isn't programmatically verifiable, so it pays for LLM judges and still sees about 4–5% disagreement between frontier models and costly false passes. **Our domain *is* programmatically verifiable:** the original service is an exact verifier, so we get zero label drift and zero false passes for free. We also borrow its priority: **a false pass (a missed drift, a wrong rule accepted) is worse than a false fail**, so thresholds are asymmetric.

**What "The Anatomy of an Agent Harness" maps to (Agent = Model + Harness):**
- **Filesystem + git = durable state:** traces, ontology and spec are versioned, and drift v1 → v2 is a git commit.
- **Context rot:** don't dump raw traces into context. Offload them to files and project only a rule's neighborhood (C4).
- **Ralph loop:** keep the fuzz → shrink → propose → verify loop running until the coverage plateau (M2), then stop.
- **Hooks for self-verification:** run `diff` after every rule change, automatically.

**Practical fit:** pi is already our coding harness, and the Pi SDK's `beforeToolCall` / after-answer hooks are where the gate and verifier would live if we build the discovery agent on it. Jev runs through OpenRouter, which we already have a key for. **Verify the Jev endpoint and model version before relying on it**, and don't put it on the critical path for the 12:00 or 20:00 deadlines.

**Decision row for DESIGN.md:**
| Harness decisions | **Code for anything checkable (gate, rule verifier = exact oracle); a System One classifier only for drift triage and model routing, via pure-function policies with fail-closed/open defaults** | *An LLM judge as the rule verifier:* probabilistic, with false passes, when an exact oracle is free. *A classifier on the replica's hot path:* not byte-exact. |

**Pitch line:** *"Most agent domains have to pay for an LLM judge. Ours has an exact one: the original service."*

## C2. Terminology to anchor the design (search terms on X)

| Topic | Search terms | How it would appear in the doc |
|---|---|---|
| Active automata learning (L\*, Angluin) | `"automata learning" black box` · `L* Angluin` | "We learn the service as an unknown state machine" |
| Protocol state fuzzing | `"protocol state fuzzing"` · `"model learning" TLS` | Precedent: reverse-engineering TLS and SSH state machines |
| Differential testing | `"differential testing"` · `"differential fuzzing"` | Name for the original-vs-replica harness |
| Stateful property testing | `"stateful property testing"` · `"model-based testing"` | Justifies sequence generation |
| Delta debugging | `"delta debugging"` · `ddmin` | Theory behind the shrinker |
| Characterization tests (Feathers) | `"characterization tests" legacy` | "The spec is a set of characterization tests" |
| Hyrum's Law | `"Hyrum's law"` | Why we replicate errors, too |
| Shadow traffic / GitHub Scientist | `"shadow traffic" migration` · `"github scientist"` | Real-world framing for legacy replacement |
| Synthetic monitoring / canary analysis | `"synthetic monitoring"` · `"canary analysis"` | Justifies the drift canary |
| API / contract drift | `"API drift"` · `"contract testing" drift` | Vocabulary for the unannounced change |
