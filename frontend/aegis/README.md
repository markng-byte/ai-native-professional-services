# AEGIS ↔ Firm OS — Integration Guide

This folder holds the **AEGIS frontend (L6)** wired to the **Firm OS backend
(L1–L5)** through the API bridge. It is the single source of truth for *what the
UI can ask the brain to do* and *how to wire any new or customised UI* to the
same backend.

> **Mental model.** AEGIS is the **face** (what users see and click). The repo
> `ai-native-professional-services` is the **brain** (agents + knowledge graph +
> tools). `src/api_bridge.py` is the **nervous system** connecting them. It is
> *not* "user UI vs admin UI" — it is "frontend product vs backend brain".

```
┌────────────────────────────────────────────┐
│  AEGIS (React/TSX)  =  L6 — THE FACE        │
│  REGO · VRIT · EIT1 · EIT2                  │
└───────────────────┬────────────────────────┘
                    │  REST + SSE   (aegisApi.ts → api_bridge.py)
┌───────────────────▼────────────────────────┐
│  FIRM OS — THE BRAIN (L1–L5)                │
│  L5 agents · L4 skills · L3 tools           │
│  L2 memory · L1 GraphRAG (Neo4j)            │
└─────────────────────────────────────────────┘
```

---

## 1. Files in this folder

| File | Role |
|------|------|
| `aegisApi.ts` | **Shared client.** Every AI call in every module goes through here. Typed methods + SSE helper + `fmt.*` formatters. This is the contract surface. |
| `rego_dashboard_v4.tsx` | Module 1 — **Macro Radar** (global regulatory monitoring) |
| `vrit_v4.tsx` | Module 2 — **Local Intel** (Vietnam/SEA hyper-local) |
| `eit_module1.tsx` | Module 3 — **Newsfeed** (signal ingestion pipeline) |
| `eit_module2.jsx` | Module 4 — **War Room** (financial scenario planning) |
| `aegisStore.ts`, `eventBus.ts` | Cross-module state (Zustand) + event bus (copy from the AEGIS project as-is) |

Backend lives at `../../src/api_bridge.py`. Agents/engine at `../../src/`.

---

## 2. The contract (read this before changing anything)

**Golden rule:** the UI sends *intent + structured parameters*, **never a raw
prompt**. Prompts live in `api_bridge.py` so they can be governed, versioned, and
routed to the right agent. This is also what keeps provider API keys server-side.

### Request
Plain JSON, typed in `aegisApi.ts`. Example:
```ts
await aegisApi.signalImpact({ signal: "MiCA Phase II enforcement", jurisdictions: ["SG","VN"] })
```

### Response envelope (every endpoint)
```jsonc
{
  "data": { /* the schema the module needs */ },
  "meta": {
    "agent": "research",            // which Firm OS agent answered
    "simulation": false,            // true when ANTHROPIC_API_KEY is unset
    "requires_human_review": true,  // compliance/drafting gate — surface in UI
    "sources": [],                  // GraphRAG provenance (L1)
    "model": "claude-sonnet-4-6",
    "run_id": "uuid",
    "timestamp": "..."
  }
}
```
`aegisApi.*` methods return `.data` directly; `fmt.*` helpers flatten `data` into
display strings for the older text panels. If you build a richer UI, read the raw
`data` instead of `fmt.*`.

### SSE contract (pipelines only — EIT1)
```
data: {"type":"stage","stage":"ingest","log":"...","progress":0.25}
data: {"type":"log","log":"  [REGULATORY] ..."}
data: {"type":"result","data":{"cards":[...]},"meta":{...}}
data: {"type":"done","log":"Pipeline complete","progress":1.0}
```

---

## 3. Module → Bridge → Agent map (the compatibility matrix)

This is the table to consult when a customer asks "can AEGIS do X?" — if the
capability maps to an existing endpoint/agent, it is compatible out of the box.

### REGO — Macro Radar  (6 call-sites)
| UI action (in `rego_dashboard_v4.tsx`) | `aegisApi` method | Bridge endpoint | Agent |
|---|---|---|---|
| MonitorTab — signal impact callout | `signalImpact` | `POST /api/research/signal-impact` | Research |
| ForecastTab — "▶ Simulate" (What-If) | `whatIf` | `POST /api/research/what-if` | Research |
| ForecastTab — risk projection chart | `riskProjection` | `POST /api/research/risk-projection` | Research |
| AdvocateTab — stakeholder list | `stakeholderMap` | `POST /api/research/stakeholder-map` | Research |
| AdvocateTab — meeting brief | `advocacyBrief` | `POST /api/drafting/advocacy-brief` | Drafting |
| Board GRC brief | `brief` | `POST /api/executive/brief` | Exec Assistant |

### VRIT — Local Intel  (2 call-sites)
| UI action (in `vrit_v4.tsx`) | `aegisApi` method | Bridge endpoint | Agent |
|---|---|---|---|
| Command terminal `sendCmd` | `localIntel` | `POST /api/compliance/local-intel` | Compliance + Research |
| Feed card "Elaborate" / "Justify" | `localIntel` | `POST /api/compliance/local-intel` | Compliance + Research |

> Also available (not yet surfaced in VRIT UI): `POST /api/compliance/sanctions-screen`,
> `POST /api/compliance/ubo-traverse`. Wire these to new buttons when a customer
> needs KYC/UBO.

### EIT1 — Newsfeed  (3 call-sites)
| UI action (in `eit_module1.tsx`) | `aegisApi` method | Bridge endpoint | Agent |
|---|---|---|---|
| Ingestion pipeline `run()` | `ingestStream` (SSE) | `POST /api/operations/ingest/stream` | Operations |
| Reports tab "▶ GENERATE" | `reportGenerate` | `POST /api/operations/report-generate` | Operations + EA |
| Onboarding org verify | `verifyOrg` | `POST /api/research/verify-org` | Research |

> Non-streaming variant available: `ingest` → `POST /api/operations/ingest`
> (returns final cards in one shot, no stage events). Use for headless/batch UIs.

### EIT2 — War Room  (4 call-sites, sequential)
| UI action (in `eit_module2.jsx`) | `aegisApi` method | Bridge endpoint | Agent |
|---|---|---|---|
| "▶ GENERATE SCENARIOS" | `scenarios` | `POST /api/executive/scenarios` | Exec Assistant |
| Strategic next-step library | `nextSteps` | `POST /api/executive/next-steps` | Exec Assistant |
| "▶ RUN SIMULATION" | `simulate` | `POST /api/executive/simulate` | Exec Assistant |
| "GENERATE IMPROVEMENTS" | `improvements` | `POST /api/executive/improvements` | Exec Assistant |

The War Room flow is a **stateful chain**: `scenarios` →pick a case→ `simulate`
with `scenario_data` + `selected_actions` → `improvements` with `sim_result` +
`target_variance`. Keep that order if you redesign the UI.

### Shared / utility
| Capability | Endpoint |
|---|---|
| Health / capability probe | `GET /api/health` |
| Engagement letter draft | `POST /api/drafting/engagement-letter` |
| Full scenario shorthand | `POST /api/executive/scenario` |

---

## 4. Running it

```bash
# Backend (the brain)
pip install -r ../../requirements.txt
export ANTHROPIC_API_KEY=sk-...          # omit → bridge runs in simulation mode
export CLAUDE_MODEL=claude-sonnet-4-6     # optional override
uvicorn src.api_bridge:app --host 0.0.0.0 --port 8000 --reload   # run from repo root

# Frontend (the face)
# In the AEGIS Vite project, set:
#   VITE_API_BASE=http://localhost:8000
# then copy these files in as siblings of eventBus.ts / aegisStore.ts.
```

No key → every endpoint returns `meta.simulation = true` and a stub payload; the
UI degrades gracefully instead of breaking. CORS is open to Vite dev ports
(`5173`, `4173`) in `api_bridge.py`.

---

## 5. How to wire a NEW or VARIANT UI to the brain

When you customise AEGIS for a client (rebrand, drop a module, add a panel) or
build a different frontend entirely, follow this so compatibility stays intact.

**A. Reusing an existing capability (most cases)**
1. Find the capability in the §3 matrix.
2. Call the matching `aegisApi.*` method from your new component.
3. Read `.data` (rich UI) or use the matching `fmt.*` (text panel).
4. Done — no backend change. Provider keys stay server-side automatically.

**B. The customer needs something new (a capability not in §3)**
1. Add a typed method in `aegisApi.ts` (keep request = structured params, no prompt).
2. Add the endpoint in `src/api_bridge.py`:
   - pick the right agent system prompt (`SYSTEM_RESEARCH` / `SYSTEM_COMPLIANCE` /
     `SYSTEM_OPERATIONS` / `SYSTEM_EA` / `SYSTEM_DRAFTING`),
   - build the prompt server-side, call `_call_claude`, parse with
     `_parse_json_response`, return via `_ok(agent, data, requires_review=…)`.
3. Update the §3 table in this README so the matrix stays the source of truth.
4. If the capability is a multi-step pipeline, model it on
   `/api/operations/ingest/stream` (SSE) so the UI can show progress.

**C. Variant versions of the same UI (A/B, tiers, white-label)**
- Keep them all pointing at the **same bridge contract**. Differences should be
  *presentation only* (which panels render, branding, role-gating via
  `aegisStore.role_level`). The `{data, meta}` envelope means a variant can show
  more or fewer fields from the same response without backend forks.
- Role/tier gating belongs in the frontend (see `role_level` lv1/lv2 in
  `aegisStore.ts`, and the "LEVEL 2 — EXECUTIVES" gate in EIT1). The backend
  stays role-agnostic; gate *what you call* and *what you render*, not the agent.

**Compatibility checklist for any UI change**
- [ ] Does the action map to a §3 endpoint? If yes → reuse, no backend work.
- [ ] Are you reading `meta.requires_human_review` and surfacing the gate?
- [ ] Are you handling `meta.simulation === true` (no-key) gracefully?
- [ ] No raw prompts or provider keys in the frontend? (grep: `api.anthropic`,
      `callClaude` must return **nothing** under `frontend/`.)
- [ ] Updated the §3 matrix if you added/changed an endpoint?

---

## 6. Design invariants (do not break)

1. **No browser → provider calls.** All AI goes through `api_bridge.py`.
   Verify: `grep -rE "api\.(anthropic|perplexity|mistral)|callClaude" frontend/` → empty.
2. **No prompts from the UI.** Requests carry structured parameters only.
3. **One client, one contract.** All modules/variants use `aegisApi.ts`.
4. **Graceful simulation.** Missing key degrades, never crashes.
5. **Human-in-the-loop is a UI duty.** When `requires_human_review` is true
   (compliance, drafting), the UI must show the gate before acting.
