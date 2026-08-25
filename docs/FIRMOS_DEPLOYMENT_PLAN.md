# firmOS Deployment Plan — OpenClaw (front-office) + Hermes (back-office)

> **Status:** Draft for review · **Scope of v1:** deterministic fixtures (no live
> Neo4j yet) · **Integration:** REST / FastAPI bridge · **Owner:** _TBD_

This document turns the three-layer proposal (firmOS brain · OpenClaw gateway ·
Hermes workers) into a sequenced, buildable plan grounded in what the repository
**actually contains today**. It is written to be handed to engineers.

---

## 0. Context — what exists today (the honest baseline)

| Asset | State | Notes |
|---|---|---|
| 9 L4 skills (`src/skills/`) | ✅ Runnable, deterministic | Uniform `run(payload: dict) -> dict`; registered in `SKILLS` |
| Eval gate (`run_evals.py`, `src/evals/`) | ✅ CI-enforced | 94/94 cases; coverage ≥10 + per-suite pass rate (0.90–1.00) |
| Assertion matcher (`src/evals/matcher.py`) | ✅ Reusable | Generic; **reused as the runtime validator engine in Phase 2** |
| Command Center UI (`src/app.py`, `engine.py`) | ✅ Runs | ⚠️ Uses `engine.py`, **not** `src/skills` (parallel logic) |
| FastAPI bridge | ❌ Not built | This plan, Phase 1 |
| Neo4j / GraphRAG / `service_catalog.json` | ❌ Not wired | Docstrings mention Neo4j; `py2neo` declared but unused. Fixtures only |
| HITL approval store / queue | ❌ Not built | Skills only *return* `requires_human_review: true` |
| `website-data-health`, Playwright ingestion | ❌ Not built | UC3; largest net-new effort |

**Skills ready to serve immediately (deterministic, green):**
`intent-classifier`, `client-lookup`, `jurisdiction-compare`, `sanctions-screen`,
`conflict-check`, `ubo-chain-traverse`, `doc-expiry-scan`,
`doc-draft-engagement-letter`, `doc-draft-banking-intro`.

---

## 1. The critical correction — two different "gates"

The proposal conflated two mechanisms. They must stay **separate**:

| | **Regression eval (CI gate)** | **Runtime contract (delivery gate)** |
|---|---|---|
| Question it answers | "Does the skill implementation still behave correctly?" | "Is *this live output* well-formed and safe to deliver?" |
| Inputs | Fixed, hardcoded in `EVAL_*.json` | Live payload from a real request |
| When it runs | On every push/PR (CI) | On every agent output, before human review |
| Exists today | ✅ `run_evals.py` | ❌ Build in Phase 2 (reuses `matcher.py`) |

> **You cannot "run Hermes's live report against `EVAL_ubo-chain-traverse.json`"** —
> that file has its own fixed inputs. Phase 2 builds the real runtime validator.

**Design rule for Hermes (deterministic-source pattern):** for compliance-grade
work, Hermes must **call the gate-verified skill as the source of truth** and let
the LLM only *narrate* the structured result — never free-hand the facts. The
skill is trusted because its eval passed; the prose is cosmetic and is what the
runtime validator + human review inspect.

---

## 2. Target architecture (corrected data flow)

```
Channels (Telegram/Zalo/Slack/UI)
        │
        ▼
┌──────────────────────────┐        ┌───────────────────────────────────────────┐
│ OpenClaw (Gateway)       │  REST  │ firmOS Bridge (src/bridge/server.py)        │
│ - intent + session mem   │──────► │  GET  /skills            (discovery)        │
│ - fast deterministic Q&A │        │  GET  /skills/{id}/schema(io contracts)     │
│ - routes deep tasks      │◄────── │  POST /skills/{id}       (invoke)           │
└─────────┬────────────────┘        │  POST /validate/{id}     (runtime contract) │
          │ job dispatch            │  POST /approvals ...     (HITL state)       │
          ▼ (Redis/webhook)         └───────────────────┬───────────────────────┘
┌──────────────────────────┐                            │  imports
│ Hermes (Workers)         │  REST                      ▼
│ - ReAct multi-step       │──────►             src/skills/*  (deterministic)
│ - calls skills as truth  │                    src/evals/matcher.py (validator)
│ - runtime-validates      │◄─────  results     [Phase 4] data adapters → Neo4j
│ - submits for HITL        │
└──────────────────────────┘
```

Domain logic, prompts (SOPs), and skills live **only** in firmOS. OpenClaw and
Hermes hold **no business rules** — they are stateless runtimes.

---

## 3. firmOS Bridge — API contract (Phase 1 target)

**Envelope (all invocations):**
```jsonc
// POST /skills/{skill_id}   Header: X-firmOS-Token: <token>
// request
{ "correlation_id": "uuid", "payload": { /* skill-specific input */ } }
// response
{ "correlation_id": "uuid", "skill_id": "jurisdiction-compare",
  "ok": true, "result": { /* skill-specific output */ },
  "audit_log_ref": "uuid|null", "duration_ms": 12 }
// error
{ "correlation_id": "uuid", "ok": false,
  "error": { "code": "ERR_VALIDATION|ERR_UNKNOWN_SKILL|ERR_INTERNAL",
             "message": "…", "field_errors": [] } }
```

**Endpoints:**
- `GET /skills` — list registered skill IDs (from `SKILLS`).
- `GET /skills/{id}/schema` — JSON Schema for input **and** output (Phase 1 adds
  pydantic models per skill; port the pattern already used in `src/tools/*`).
- `POST /skills/{id}` — validate input → run skill → return envelope.
- `POST /validate/{id}` — Phase 2: check a live result payload against the skill's
  output contract; returns `{ "valid": bool, "violations": [...] }`.
- `POST /approvals`, `GET /approvals/{id}`, `POST /approvals/{id}/decision` —
  Phase 3 HITL.

**Cross-cutting:** static bearer token in v1 (`X-firmOS-Token`); every request/
response logged with `correlation_id`; compliance skills already emit
`audit_log_ref` — surface it in the envelope.

---

## 4. Phased roadmap

Each phase lists **Goal · Deliverables · Acceptance criteria · Depends on**.
Phases 1–3 are all **fixtures-first** (per decision) and unblock UC1 + UC2.

### Phase 1 — Bridge + schemas + auth  *(unblocks UC1 end-to-end)*
- **Goal:** Any runtime can discover and invoke gate-verified skills over HTTP.
- **Deliverables:**
  - `src/bridge/server.py` (FastAPI) implementing `/skills`, `/skills/{id}/schema`,
    `POST /skills/{id}`.
  - `src/skills/schemas.py` — one pydantic `Input`/`Output` model per skill (9×2).
  - Bearer-token auth; structured error envelope; `correlation_id` logging.
  - `tests/test_bridge.py` — smoke test hitting every skill through the API.
  - `requirements.txt`: add `fastapi`, `uvicorn[standard]`, `pydantic`.
  - `docs/BRIDGE_API.md` — the contract in §3, for OpenClaw/Hermes teams.
- **Acceptance:** `uvicorn src.bridge.server:app` serves all 9 skills; input
  validation rejects malformed payloads with `ERR_VALIDATION`; smoke test green;
  CI eval gate still passes unchanged.
- **Depends on:** nothing (skills already green).

### Phase 2 — Runtime output-contract validator  *(makes UC2 "eval-gated delivery" real)*
- **Goal:** Score a **live** agent output before it reaches a human.
- **Deliverables:**
  - `src/validate/contracts.py` — per-skill output JSON Schema + rule set
    (reusing `matcher.py` for assertions like `requires_human_review == true`,
    `audit_log_ref` present, `screen_result in {...}`).
  - `POST /validate/{id}` endpoint returning violations.
  - (Optional) `src/validate/judge.py` — LLM-judge for free-form narrative
    faithfulness vs. the structured `result` (deterministic-source pattern).
  - `tests/test_validator.py`.
- **Acceptance:** a well-formed `ubo-chain-traverse` result validates; a tampered
  one (missing `audit_log_ref`, or `requires_human_review` dropped) fails with a
  precise violation. Hermes can gate on a non-2xx from `/validate`.
- **Depends on:** Phase 1.

### Phase 3 — HITL approval store  *(turns the flag into a real stop-gate)*
- **Goal:** `requires_human_review: true` becomes an enforced pause, not a hint.
- **Deliverables:**
  - Approval store (SQLite for local v1; Postgres-ready interface) with state
    machine `DRAFTED → PENDING_REVIEW → APPROVED | REJECTED`.
  - `/approvals` endpoints; each record links `correlation_id`, skill, result,
    `audit_log_ref`, reviewer, decision, timestamp (immutable audit trail — see
    `governance/GOVERNANCE.md`).
  - OpenClaw surfaces pending items to the reviewer channel; delivery blocked
    until `APPROVED`.
- **Acceptance:** a drafting/compliance result cannot be delivered without an
  `APPROVED` decision recorded; rejections are logged with reason.
- **Depends on:** Phase 1 (2 recommended).

### Phase 4 — Live-data adapters  *(fixtures → Neo4j / service_catalog, same interface)*
- **Goal:** Replace fixtures with real data **without changing the skill contract**.
- **Deliverables:**
  - `src/skills/adapters/` — a data-access interface; fixture impl (default) +
    Neo4j/`service_catalog.json` impl selected by env var.
  - Migrate read-heavy skills first: `jurisdiction-compare`, `client-lookup`,
    `ubo-chain-traverse`, `doc-expiry-scan`.
  - A **new test tier** (`tests/integration/`) that runs the suites against the
    live adapter — the existing `EVAL_*.json` stay as the fixture-contract tier.
- **Acceptance:** with `FIRMOS_DATA=neo4j`, skills return live data and pass the
  integration tier; with `FIRMOS_DATA=fixtures`, existing evals still pass.
- **Depends on:** Phase 1; standing up Neo4j + seeding `service_catalog.json`.

### Phase 5 — Ingestion + `website-data-health`  *(UC3, largest new build)*
- **Goal:** Crawl service portals, normalize into `service_catalog.json`/Neo4j,
  and QA the data.
- **Deliverables:**
  - `src/ingestion/` — Playwright/Chromium crawlers (env already has Chromium at
    `/opt/pw-browsers`; do **not** re-download).
  - Normalizer → `service_catalog.json` schema; Neo4j upsert.
  - New skill `website-data-health` + `EVAL_website-data-health.json` (≥10 cases)
    checking duplicates, missing fields, price conflicts — **must clear the same
    gate as every other skill.**
- **Acceptance:** scheduled run produces a QA report artifact; new skill is green
  in CI; OpenClaw can surface the report to the ops manager.
- **Depends on:** Phase 4.

### Cross-cutting quick win — unify the UI onto skills
- Refactor `engine.py`'s pipeline to call `src/skills/*` (remove the parallel
  simulation logic). The Command Center then becomes a **free local test harness**
  for the bridge and guarantees the UI shows exactly what the gate verifies.
- Can slot in right after Phase 1. Low risk, high consistency payoff.

---

## 5. Use-case realization map

| Use case | Enabled after | How |
|---|---|---|
| **UC1** Fast jurisdiction/service comparison | **Phase 1** | OpenClaw → `POST /skills/intent-classifier` then `/skills/jurisdiction-compare`; formats the returned table. Deterministic, already green. |
| **UC2** Deep compliance / UBO audit | **Phase 2 (+3)** | Hermes calls `ubo-chain-traverse` + `sanctions-screen` as source of truth → `/validate` → HITL approval → deliver. |
| **UC3** Web ingestion + data-health | **Phase 5** | Hermes runs Playwright ingestion → normalize → `website-data-health` → OpenClaw reports. |

---

## 6. What OpenClaw & Hermes must implement (their side of the contract)

_firmOS does not control these runtimes; these are the integration expectations._
- **OpenClaw:** hold `X-firmOS-Token`; call `/skills` on boot for discovery;
  classify + route; for deep tasks, dispatch a job carrying `correlation_id`;
  render pending-approval items to the reviewer channel.
- **Hermes:** for any factual/compliance step, **call the skill, don't invent**;
  run `/validate/{id}` on its output; only submit to HITL on a valid result;
  never deliver a client-facing artifact without an `APPROVED` decision.

> ⚠️ **Open confirmation:** the exact SDK/protocol surface of OpenClaw and Hermes
> is unverified. The REST bridge is deliberately framework-agnostic; if either
> runtime is MCP-native, add a thin MCP shim over the same skill registry rather
> than changing the skills.

---

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Treating evals as a live validator (false safety) | §1 separation; Phase 2 runtime validator |
| Agents free-handing compliance facts | Deterministic-source pattern (Hermes calls skills) |
| PII egress across chat channels | Bridge auth + Phase 3 audit trail before any live data (Phase 4) |
| Fixture logic silently diverging from UI | Cross-cutting UI-unification task |
| Neo4j swap breaking verified behavior | Adapter interface + integration test tier keeps the eval contract intact |

---

## 8. Immediate next actions
1. **Confirm this plan** (esp. §1 correction and the REST decision).
2. Approve **Phase 1** scope → I build `src/bridge/server.py`, the 9 pydantic
   schema pairs, auth, smoke tests, and `docs/BRIDGE_API.md`, all fixtures-first.
3. In parallel, share whatever OpenClaw/Hermes expose for integration so §6 can be
   made concrete.

_Restarting from the merged `main`, all Phase-1 work lands on a fresh branch with
its own PR and stays behind the existing eval gate._
