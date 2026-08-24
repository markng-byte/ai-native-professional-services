# RM Co-pilot — Architecture Audit (Phase 0)

> **Session:** first session, AUDIT ONLY — no production code modified.
> **Audited commit:** `5624803` (= `main` @ `15e5336` + deployment-plan doc)
> **Baseline verified:** `python run_evals.py` → **94/94 cases, 9/9 skills, GATE PASSED, exit 0**
> **Method:** direct repository inspection (`git`, `find`, `grep`, file reads), not recollection.

This document answers §3.A–H of the master prompt.

---

## A. What already exists?

### A.1 Verified-green core (production-quality)

| Asset | Path | Evidence |
|---|---|---|
| 9 deterministic L4 skills | `src/skills/*.py` | Uniform `run(payload: dict) -> dict`; `SKILLS` registry in `__init__.py` |
| Eval gate (regression, Layer 1) | `run_evals.py`, `src/evals/runner.py` | 94/94 green; enforces coverage ≥10 **and** per-suite pass rate (0.90–1.00); exits non-zero |
| Generic assertion matcher | `src/evals/matcher.py` | Skill-agnostic; declarative suffix/prefix vocabulary |
| Eval suites | `L4_Skills/evals/EVAL_*.json` | 9 suites, 94 cases |
| CI enforcement | `.github/workflows/eval-gate.yml` | Runs on every push + PR; blocks merge |

Skills present and green: `intent-classifier`, `client-lookup`, `jurisdiction-compare`,
`sanctions-screen`, `conflict-check`, `ubo-chain-traverse`, `doc-expiry-scan`,
`doc-draft-engagement-letter`, `doc-draft-banking-intro`.

### A.2 Specification assets (documentation-quality, not executable)

| Asset | Path | Relevance to RM Co-pilot |
|---|---|---|
| **Approval Matrix** | `governance/GOVERNANCE.md` §2 | ⭐ **Rows 4, 5, 7 name "Relationship Manager" as the approver.** The RM actor is already a first-class governance role. |
| **Audit-log field spec** | `governance/GOVERNANCE.md` §5.1 | Per-event-type fields + retention (2y/7y/indefinite) + immutability flags |
| **Human override procedure** | `governance/GOVERNANCE.md` §8 | Override authority levels + workflow |
| **Tool registry** | `L3_Tools/TOOL_REGISTRY.md` §1 | ⭐ Salesforce specified as **MCP server, OAuth 2.0, per-agent service account**, with explicit READ/WRITE scoping per agent and fallback behavior |
| **Memory schema** | `L2_Memory/MEMORY_SCHEMA.md` §1 | 4 memory types with write/read ACLs, PII handling, retention |
| **Agent specs** | `L5_Agents/AGENT_SPEC_*.md` | 6 agents incl. Orchestrator, Compliance, Drafting, Operations |
| **Deployment plan** | `docs/FIRMOS_DEPLOYMENT_PLAN.md` | OpenClaw/Hermes REST bridge plan (see §H.1 — **not** an RM plan) |

### A.3 Experimental / prototype

| Asset | Path | Why experimental |
|---|---|---|
| CrewAI scaffold | `src/agents.py`, `tasks.py`, `main.py` | Hardcodes `claude-3-opus-20240229` (stale model id); compliance agent commented out; not covered by any test or eval |
| CrewAI tools | `src/tools/*.py` | Only 2 of 9 skills; **re-implements skill logic independently** (see C.1) |
| Command Center UI | `src/app.py`, `src/engine.py` | Runs; but `engine.py` holds a **third** copy of business logic (see C.1) |

### A.4 Confirmed ABSENT (verified by grep across `*.py`)

`tests/` directory · FastAPI/bridge (`fastapi`, `uvicorn` → 0 hits) · MCP code (`mcp` → 0 hits in `*.py`) ·
Salesforce adapter (`salesforce` in code → only a docstring mention in `client_lookup.py`) ·
authorization/authz code (`authoriz` → 0 hits) · OAuth (0 hits) · approval state machine ·
runtime output validator · correlation-id plumbing · **`opportunity` → 0 hits in the entire repo (code *and* docs)**.

---

## B. What is production-quality?

Only **A.1**. Specifically: the 9 skills, the matcher, the runner, the eval suites, and the CI gate.
These are the protected baseline under master-prompt §5 and must not be weakened.

**Qualifier — "production-quality" means contract-and-behavior quality, not production-data quality.**
Every skill reads in-repo fixtures. `client_lookup.py` returns a hardcoded `CLIENTS` dict; its
"CRM/Salesforce" reference exists only in the module docstring. Per §27: **fixture ≠ Salesforce.**

---

## C. What is experimental?

### C.1 ⚠️ FINDING — business logic is **triplicated**, not duplicated

The deployment plan (and master-prompt §14) flags *one* duplication: UI → `engine.py` instead of
`src/skills`. Inspection shows **three independent implementations** of the same two capabilities:

| Capability | Impl 1 (verified/gated) | Impl 2 | Impl 3 |
|---|---|---|---|
| Intent classification | `src/skills/intent_classifier.py` (`_classify`) | `src/engine.py::classify()` | `src/tools/intent_classifier_tool.py::_run()` |
| Jurisdiction data + compare | `src/skills/jurisdiction_compare.py` | `src/engine.py::_JURIS_DATA` | `src/tools/jurisdiction_compare_tool.py` (own `mock_data`) |

All three carry **separate copies of the jurisdiction fixture** (verified: the literal `$2,500`
appears in all three files). Only Impl 1 is covered by the eval gate.

**Consequence:** the gate can be green while the UI and the CrewAI runtime return *different
answers* for the same question. This is a live correctness risk for an RM-facing product and is a
strictly larger problem than §14 describes.

### C.2 Other experimental items
- CrewAI scaffold (stale model id, partially commented out, untested).
- `src/tools/` pydantic pattern is **useful** (it is the only existing example of typed skill I/O)
  even though its logic must not survive.

---

## D. What can be reused?

| Reusable asset | Reused as | Confidence |
|---|---|---|
| `src/skills/*` + `SKILLS` registry | The deterministic source of truth (§12) behind every RM workflow | High |
| `src/evals/matcher.py` | Engine for **Layer 2 tool-contract** and **Layer 4 runtime** validation | High |
| `run_evals.py` + CI gate | Layer 1 regression, unchanged | High |
| `GOVERNANCE.md` §2 Approval Matrix | The **authorization + HITL policy source**; rows 4/5/7 already define RM-approved actions | High |
| `GOVERNANCE.md` §5.1 audit fields | The audit-record schema for §22 | High |
| `TOOL_REGISTRY.md` §1 Salesforce row | The **authorization model** for the Salesforce adapter (OAuth, per-agent scope, fallback) | Medium–High |
| `MEMORY_SCHEMA.md` Working memory | The §7.3 agent-memory definition | Medium (see H.3) |
| `src/tools/*` pydantic **pattern** | Template for per-skill/tool I/O schemas | Pattern only — **discard the logic** |

---

## E. What must be refactored?

| # | Item | Required change | Risk if skipped |
|---|---|---|---|
| E1 | `src/engine.py` business logic | Delegate to `src/skills/*`; keep only presentation/pipeline sequencing | UI contradicts the gated skills |
| E2 | `src/tools/*.py` | Re-implement as thin wrappers over `SKILLS`; delete private logic + fixture copies | CrewAI runtime contradicts gated skills |
| E3 | Jurisdiction fixture | Collapse 3 copies → 1 owned by the skill layer | Silent data drift |
| E4 | `requires_human_review` | Today a returned **flag** only. Must become an enforced gate. Per §27: **flag ≠ enforced HITL** | False sense of governance |
| E5 | CrewAI scaffold model id | `claude-3-opus-20240229` is stale | Runtime failure / wrong model |

E1–E3 are **prerequisites** for the RM Co-pilot: an RM-facing answer must not depend on which
surface it came from.

---

## F. What must be newly built?

Ordered by dependency.

| # | New component | Notes |
|---|---|---|
| F1 | **RM/Opportunity domain model** | ⚠️ Largest gap. `opportunity` appears **nowhere** in the repo. Needs entities: Opportunity, Stage, Activity, Task, Engagement, RenewalStatus + fixtures |
| F2 | **Business capability tools (Tier 1 read)** | `search_client`, `get_rm_client_context`, `get_opportunity_context`, `get_client_history`, `get_open_tasks`, `get_engagements`, `get_documents`, `get_renewal_status` |
| F3 | **Tool contract layer** | Per-tool pydantic input/output schemas + Layer-2 contract eval |
| F4 | **RM workflows (Tier 2)** | `rm-client-summary`, `rm-next-best-action`, `rm-followup-draft`, `rm-opportunity-review` |
| F5 | **Layer 3 agent-workflow evals** | The 10 RM scenarios in §13 |
| F6 | **Layer 4 runtime validator** | Reuses `matcher.py`; validates live output pre-delivery |
| F7 | **HITL approval store** | `DRAFTED → PENDING_REVIEW → APPROVED/REJECTED` + audit record |
| F8 | **Authorization layer** | Actor-based (§21); RM scope ≠ client-portal scope |
| F9 | **Correlation-id + audit plumbing** | Per `GOVERNANCE.md` §5.1 fields |
| F10 | **Transport (REST bridge and/or MCP)** | Only if a runtime actually needs it — see §H.2 |
| F11 | **`tests/`** | No test directory exists; needed for F3 |

---

## G. What should be explicitly deferred?

Per master-prompt §20, and confirmed as non-blocking by this audit:

- Client Portal AI, Mobile AI, Meta/WhatsApp agents
- Autonomous client communication; autonomous CRM mutation (Tier 3 writes)
- Full Neo4j migration; `service_catalog.json`; website ingestion / `website-data-health`
- Broad enterprise agent-platform rewrite
- **Production Salesforce** (Phase 5 sandbox at the earliest — no credentials present or requested)
- OpenClaw/Hermes runtime integration (deferred until RM workflows exist to consume)

---

## H. What conflicts with an RM-Co-pilot-first strategy?

### H.1 ⚠️ CONFLICT — the referenced "RM Co-pilot Deployment Plan" does not exist
Master-prompt §3 instructs inspection of *"the current RM Co-pilot Deployment Plan."*
The only plan in the repo is `docs/FIRMOS_DEPLOYMENT_PLAN.md`, which is an **OpenClaw/Hermes
runtime-integration plan**. It contains **zero** RM, opportunity, or Salesforce-capability content
(verified: `opportunity` → 0 hits repo-wide).

**Classification:** *outdated planning assumption* (the plan predates the RM-first thesis).
**Proposed reconciliation:** keep its four cross-cutting decisions (regression-vs-runtime eval
separation; deterministic-source principle; fixture-first; adapter-preserves-contract), and
**re-sequence its phases around RM Co-pilot** rather than executing it as written. Its Phase 1
(bridge) and Phase 5 (ingestion) are **not** RM prerequisites.

### H.2 ⚠️ CONFLICT — plan Phase 1 (bridge) vs. RM-first minimality
The deployment plan makes the FastAPI bridge Phase 1. Master-prompt §19 says build the bridge
*"only if required by actual repository state,"* and §28 says build the smallest system that proves
the thesis. **The RM Co-pilot thesis can be proven end-to-end with no network transport at all**
(workflows + tools + evals, exercised in-process and through the existing Streamlit UI).
**Recommendation:** demote the bridge; build it when an external runtime (OpenClaw/Hermes) is
actually integrated. Transport is not the thesis.

### H.3 ⚠️ CONFLICT — Episodic memory vs. "memory must not become a shadow CRM" (§7.3)
`MEMORY_SCHEMA.md` defines **Episodic memory** as *"per-client session history: questions,
decisions, outputs, flags,"* retained *"indefinitely while client active."* Master-prompt §7.3
restricts agent memory to conversational context and forbids a shadow CRM.
**Classification:** *architectural conflict*, currently latent (no memory store is implemented).
**Proposed reconciliation:** for RM v1, agent memory = **Working memory only**. Episodic memory is
either deferred, or explicitly re-scoped as an *audit/interaction log* (not a queryable client-truth
store). **This needs a human decision before any memory persistence is built.**

### H.4 ⚠️ CONFLICT — `TOOL_REGISTRY` grants agents direct Salesforce MCP access
`TOOL_REGISTRY.md` row 2.0 permits *"Orchestrator (READ – client lookup), Operations Agent
(READ/WRITE – mandate updates), Compliance Agent (WRITE – risk flags only)"* directly against the
Salesforce **MCP server**. Master-prompt §8 forbids raw CRUD as the agent's public interface and
§15 states MCP is transport, not architecture.
**Classification:** *architectural conflict.*
**Proposed reconciliation:** insert the business-capability layer between agent and Salesforce; the
registry's **permission scoping is retained** as the adapter's authorization policy, but agents bind
to capabilities (`get_opportunity_context`), never to `salesforce.query()`.

### H.5 Non-conflict worth noting (positive alignment)
`GOVERNANCE.md` rows 4/5/7 already designate the **Relationship Manager** as approver for
engagement-letter sends, banking-intro sends, and client-facing research. The RM-first thesis is
**already consistent with existing governance** — RM Co-pilot formalizes a role the architecture
anticipated.

### H.6 Process conflict — branch base
`docs/FIRMOS_DEPLOYMENT_PLAN.md` exists only on `claude/project-completion-check-ooyc1e`
(commit `5624803`), **not on `main`**. To keep the referenced plan present on the feature branch,
`feature/rm-copilot` is based on `5624803` (= `main` + that one doc commit). No user work discarded;
no history rewritten. Flagged for awareness — if the plan doc should be excluded, rebase onto
`origin/main`.

---

## Summary judgement

The repository is a **strong deterministic foundation with essentially no application layer**.
Reusability is high (skills, matcher, gate, governance policy). The RM Co-pilot's blocking gap is
**not** transport or infrastructure — it is the **absent opportunity/CRM domain model** (F1) and the
**absent business-capability layer** (F2), plus the **triplicated business logic** (C.1) that would
otherwise let the RM see inconsistent answers.
