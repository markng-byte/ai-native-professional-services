# RM Sales Co-pilot — Use Case Definition (v1)

> **Status:** Phase 1 delivered (domain model + Tier 1 capability layer + Layer 2 contract eval).
> Phases 2+ awaiting approval. · **Branch:** `feature/rm-copilot` · **PR:** #4
> **Thesis:** firmOS can safely combine CRM data, domain knowledge, deterministic skills,
> business tools and agent reasoning into **governed, grounded, auditable decision support** for an
> internal Relationship Manager.
> **The RM remains the decision-maker. The system is assistive, not autonomous.**

---

## 1. Success definition

**Success is NOT** "the LLM can talk to Salesforce."

**Success IS:** for a real RM scenario, firmOS can

1. assemble grounded client + opportunity context from governed capability tools,
2. state explicitly what it does **not** know,
3. recommend a next action with a traceable reason,
4. draft a follow-up that is gated on human review,
5. and produce an auditable record of all of it.

**Explicit non-goals for v1:** autonomous CRM writes, autonomous client communication, production
Salesforce, client-portal/mobile/Meta channels.

---

## 2. Actor & authorization scope

| Actor | Sees | Must never see |
|---|---|---|
| **Relationship Manager** | Internal CRM context for **their assigned** clients/opportunities; firmOS domain knowledge | Clients not assigned to them; compliance internals beyond their approval rights |
| *(deferred)* Client Portal user | Client-authorized context only | Any internal CRM commentary |

Authorization is designed around the **actor**, not the tool (§21). RM scope ≠ client scope; a tool
being *able* to retrieve data is not authorization to expose it.

> Alignment: `governance/GOVERNANCE.md` §2 already names the **Relationship Manager** as the human
> approver for engagement-letter sends (row 4), banking-intro sends (row 5), and client-facing
> research (row 7). RM Co-pilot formalizes a role the architecture already anticipated.

---

## 3. Information architecture (three separate domains)

| Domain | Answers | Source in v1 | Must not become |
|---|---|---|---|
| **CRM / transactional** | "What is happening with this client?" | **Fixtures** (Salesforce sandbox deferred to Phase 5) | The knowledge base |
| **firmOS knowledge** | "What does firmOS know about this topic?" | Existing L1/L2 specs + deterministic skills | A CRM |
| **Agent memory** | "What is this RM working on right now?" | **Working memory only** (session, selected client/opportunity, objective) | A shadow CRM |

> **Open decision D6:** `L2_Memory/MEMORY_SCHEMA.md` defines *Episodic* memory as indefinite
> per-client history — which would be a shadow CRM under §7.3. v1 default: **defer Episodic
> persistence**; use Working memory only.

---

## 4. Target workflow

```
RM selects client / opportunity
        ↓
retrieve client context        ── Tier 1 capability tools (governed, fixture-backed)
retrieve opportunity context   ──
retrieve relevant knowledge    ── deterministic skills (gated source of truth)
        ↓
identify gaps / risks / needs  ── explicit unknown vs known
        ↓
recommend next best action     ── structured evidence + traceable reason
        ↓
draft follow-up                ── requires_human_review = true
        ↓
runtime validation (Layer 4)   ── contract check before delivery
        ↓
RM review                      ── HITL: DRAFTED → PENDING_REVIEW → APPROVED / REJECTED
        ↓
(optional) proposed CRM action ── Tier 3, NOT enabled in v1
```

**Missing-information rule:** the co-pilot must never invent facts. Every gap is classified as one
of: `unknown` · `unavailable` · `requires_rm_input` · `requires_specialist_escalation`.

---

## 5. Capability tools (Tier 1 — read, fixture-backed)

`search_client` · `get_rm_client_context` · `get_opportunity_context` · `get_client_history` ·
`get_open_tasks` · `get_client_engagements` · `get_client_documents` · `get_renewal_status`

**Status: ✅ implemented in Phase 1** — `src/capabilities/tools.py`, registry `CAPABILITIES`.
All eight are deterministic, fixture-backed, actor-authorized and envelope-returning.

**Contract rule:** these are **business capabilities**, not CRUD. No `salesforce.query()` is ever
exposed to an agent. The contract must survive a Salesforce object-model change:

```
RM Agent → Business Capability Tool → Data Adapter → (fixtures | Salesforce sandbox)
```

> **Open decision D3:** `get_rm_client_context` should **wrap** the existing gated `client-lookup`
> skill rather than reimplement it (§26 forbids duplicated logic).

---

## 6. RM workflows (Tier 2 — recommend / draft)

Build order reflects thesis value, not the order listed in the prompt.

| # | Workflow | Produces |
|---|---|---|
| 1 | `rm-client-summary` | `client_summary`, `opportunity_summary`, `current_stage`, `recent_activity`, `open_items`, `known_needs`, `missing_information`, `risk_flags` |
| 2 | `rm-next-best-action` | `recommended_action`, `reason`, `priority`, `required_information`, `suggested_next_question` |
| 3 | `rm-opportunity-review` | `stage_assessment`, `aging`, `conversion_risk`, `missing_actions`, `recommended_actions` |
| 4 | `rm-followup-draft` | `draft`, `supporting_facts`, `requires_human_review` |

> **Open decision D4:** these are specified as **deterministic heuristics emitting structured
> evidence** (so they remain Layer-1 gate-able), with optional non-authoritative LLM narration.
> **Open decision D5:** v1 core therefore requires **no LLM**.

---

## 7. Deterministic-source principle

For anything factual or regulated — sanctions, UBO, conflicts, document validity, jurisdiction
facts — the **existing gated skill is the source of truth**. The reasoning layer may orchestrate,
summarize, explain, draft and recommend *from structured evidence*; it may never substitute
generation for a verified computation.

```
deterministic skill → structured result → agent explanation      ✅
agent guesses result                                              ❌
```

---

## 8. Evaluation plan

| Layer | Scope | Status |
|---|---|---|
| **L1 Regression** | Existing 9 skills + new RM workflow logic, fixed fixtures, CI | ✅ exists (94/94) — **must stay green** |
| **L2 Tool contract** | Schema, input validation, authorization, output contract, errors, correlation_id, audit ref | 🔲 new |
| **L3 Agent workflow** | The 10 RM scenarios (new lead w/ incomplete info; new-jurisdiction interest; stalled opp; overdue follow-up; missing docs; cross-sell; high-value + weak activity; conflicting CRM info; insufficient info; escalation-required) | 🔲 new |
| **L4 Runtime validation** | Live output validated pre-delivery (shares `matcher.py` with L2) | 🔲 new |
| **L5 Human RM review** | Actual usefulness | ⏭ pilot |

**Protected:** L1 semantics. No eval deletion, threshold weakening, matcher-semantics change to
force a pass, or CI bypass — any change to eval semantics requires explicit documentation and
approval (§5, §23.3).

---

## 9. Governance & audit

- **HITL:** `requires_human_review` is currently only a **returned flag** — v1 must make it an
  enforced stop (`DRAFTED → PENDING_REVIEW → APPROVED / REJECTED`). Per §27: **flag ≠ enforced HITL**.
- **Audit record fields** follow `governance/GOVERNANCE.md` §5.1: `correlation_id`, actor identity,
  runtime identity, client/opportunity id, tool, request/result status, authorization result,
  audit reference, approval state, timestamp. No unnecessary sensitive data logged.
- **Data:** synthetic/fixture only. No production PII in local development.

---

## 10. Out of scope for v1

Client Portal AI · Mobile AI · Meta/WhatsApp agents · autonomous client communication ·
autonomous CRM mutation (Tier 3) · full Neo4j migration · website ingestion · production Salesforce ·
OpenClaw/Hermes runtime integration · MCP transport · FastAPI bridge (deferred — not on the RM
critical path; see the architecture audit §H.2).

Future channels must be able to reuse the **same capability layer** without modification — that is
the reusability test for every core component built here.
