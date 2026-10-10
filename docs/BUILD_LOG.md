# Build Log

Chronological record of what we built, the decisions we made, and why. Times are Bogotá (UTC-5), 2026-10-10.

| Time | Phase | Entry |
|---|---|---|
| 10:00 | Choice | Read both briefs. Reto 1 = screen agent (noVNC, full GUI, unseen app, 5 min/task). Reto 2 = black-box HTTP replacement (exact-match, `/__reset` before each test). |
| 10:10 | Choice | Ran two adversarial reviews of our reasoning. Accepted: don't pick the problem to fit a stack; self-healing by replaying checkpoints is unsafe on a UI with side effects; keep the shrinker simple. Rejected: "100% on our corpus = identical" (coverage is the real risk); DOM injection for Reto 1 (noVNC exposes only pixels). |
| 10:19 | Design | Drafted `docs/DESIGN.md`: pure `handle(state, req)` core, actor-model serialization, hosting chosen by fingerprinting the original's edge headers (Cloudflare and Fly proxies inject headers). |
