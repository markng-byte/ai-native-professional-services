# CLAUDE.md — Repo invariants & guardrails

Rules that must hold across the AEGIS codebase. Do **not** break these when making
changes. They are compiled from the architecture in [`PRD.md`](PRD.md) and
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Invariants (do not violate)

1. **Provider keys stay server-side.** No Anthropic/Perplexity/Mistral (or any
   provider) API key ever reaches the browser. Every AI call routes through
   `src/api_bridge.py` → Firm OS agents. The frontend must not make direct
   browser→provider calls.

2. **BYO user key is request-scoped only.** A user-supplied key (from Settings)
   lives in the browser (`localStorage`) and, server-side, only inside a
   per-request `contextvar` (`UserKeyMiddleware`). It is **never logged and never
   persisted** server-side. `_active_key()` / `_active_model()` prefer the user
   key over the env key. BYO-key requests bypass the per-IP rate limiter.

3. **Every bridge endpoint returns the `{ data, meta }` envelope.** `meta`
   carries `agent`, `simulation`, `requires_human_review`, `sources`, `model`,
   `run_id`, `timestamp`. Don't return bare payloads to the UI.

4. **Human-in-the-loop for compliance.** Compliance outputs set
   `requires_human_review`; agents never auto-approve compliance concerns.

5. **Simulation stubs match the real schema, per endpoint.** When no key is set,
   each endpoint returns a `sim=` stub shaped **exactly** like its live response,
   so the UI renders identically with or without a key. Never return a generic
   `{"_simulation": true}` object to a typed UI surface.

6. **`signals` (Signal Feed) is in-memory only.** Not persisted; reset on
   `clearUserProfile()`. Don't add it to the store's `partialize` list.

7. **GraphRAG: real result first, labelled fallback second.** Query the graph
   before falling back, and label simulation clearly when no graph data matches.
   NetworkX is the default backend; Neo4j activates via `NEO4J_URI` with no code
   change.

8. **Single-origin deploy.** One FastAPI process serves the built UI and `/api`
   (`/api` takes precedence). A public link is protected by BasicAuth
   (`DEMO_PASSWORD`) + per-IP rate limit.

9. **Eval-gated.** No L4 skill / L5 agent goes live without ≥90% pass on its
   `EVAL.json`.

---

## Anti-patterns (do not introduce; existing ones are debt to remove)

- **Hardcoded frontend fallback data.** Do **not** paper over a broken or wrong
  API response with a large inline hardcoded data block in the frontend (e.g.
  EIT2 War Room's inline bull/base/bear, next-steps, simulation, and
  improvements fallbacks). If the API returns the wrong shape, **fix the
  contract or surface the error** (a visible banner) — never silently render
  fabricated data that looks real to the user. The sanctioned simulation path is
  the backend's per-endpoint `sim=` stub (invariant #5), which is honestly
  flagged via `meta.simulation`. Frontend hardcoded fallbacks hide contract
  breaks and mislead users; the ones that remain are tech debt, not a pattern to
  copy.

---

## Workflow

- Develop on feature branches; do not push directly to `main`.
- CI must pass before merge: `npm run build`, `python tests/test_graph.py`,
  `python run_evals.py` (see `.github/workflows/ci.yml`).
