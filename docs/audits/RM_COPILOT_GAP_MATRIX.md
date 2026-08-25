# RM Co-pilot — Implementation Gap Matrix (Phase 0, §24 Step 8)

Categories: **EXISTING** (works today) · **REUSABLE** (use as-is) · **REFACTOR** (change without
breaking) · **NEW** (build) · **DEFERRED** (out of v1) · **HUMAN DECISION** (blocked on an answer)

Change classification per §17: **A** = generic firmOS core · **B** = RM-specific ·
**C** = experimental · **D** = deferred.

---

## EXISTING — verified working, protected baseline

| Item | Path | Evidence | Class |
|---|---|---|---|
| 9 deterministic skills | `src/skills/*` | 94/94 green | A |
| Regression eval gate (L1) | `run_evals.py`, `src/evals/runner.py` | exit 0, CI-enforced | A |
| Assertion matcher | `src/evals/matcher.py` | skill-agnostic | A |
| CI workflow | `.github/workflows/eval-gate.yml` | runs on push + PR | A |
| Governance policy | `governance/GOVERNANCE.md` | approval matrix, audit fields, override | A |
| Tool registry (spec) | `L3_Tools/TOOL_REGISTRY.md` | Salesforce OAuth + per-agent scope | A |

---

## REUSABLE — adopt without modification

| Item | Reused as | Class |
|---|---|---|
| `SKILLS` registry + `run(payload)->dict` contract | Deterministic source of truth for RM workflows | A |
| `matcher.py` | Shared engine for **L2 tool-contract** and **L4 runtime** validation | A |
| `GOVERNANCE.md` §2 approval matrix | Authorization + HITL policy (RM already named approver, rows 4/5/7) | A |
| `GOVERNANCE.md` §5.1 audit fields | Audit-record schema | A |
| `TOOL_REGISTRY.md` §1 Salesforce row | Adapter-level authorization policy (**not** an agent-level grant — see conflict H.4) | A |
| `src/tools/*` pydantic **pattern** | Template for typed tool I/O (**pattern only, discard logic**) | A |

---

## REFACTOR — must change, must not break evals

| ID | Item | Change | Risk | Class |
|---|---|---|---|---|
| R1 | `src/engine.py` | Delegate business logic to `src/skills/*`; keep presentation only | UI contradicts gate | A |
| R2 | `src/tools/*.py` | Thin wrappers over `SKILLS`; delete private logic + fixture copies | Runtime contradicts gate | A |
| R3 | Jurisdiction fixture (3 copies) | Collapse to one owned by the skill layer | Silent data drift | A |
| R4 | Data access inside skills | Extract adapter seam **behind** the existing contract — eval behavior must stay byte-identical | Breaks protected baseline (§5 vs §6 collision) | A |
| R5 | `requires_human_review` | Flag → enforced state machine | False governance | A |
| R6 | CrewAI model id `claude-3-opus-20240229` | Update or quarantine scaffold | Runtime failure | C |

---

## NEW — build (dependency-ordered)

| ID | Item | Depends on | Class |
|---|---|---|---|
| N1 | **Opportunity/RM domain model + fixtures** (`opportunity` = 0 hits repo-wide) | D1 | B |
| N2 | Tier 1 capability tools (8 read tools) | N1, D2, D3 | A (contract) / B (RM shape) |
| N3 | Tool schemas + **L2 contract eval** | N2 | A |
| N4 | `tests/` directory (none exists) | — | A |
| N5 | RM workflows: `rm-client-summary` → `rm-next-best-action` → `rm-opportunity-review` → `rm-followup-draft` | N2, D4, D5 | B |
| N6 | **L3 agent-workflow evals** (10 scenarios) | N5 | B |
| N7 | **L4 runtime validator** (reuses `matcher.py`) | N3 | A |
| N8 | **HITL approval store** `DRAFTED→PENDING_REVIEW→APPROVED/REJECTED` | N7 | A |
| N9 | Authorization layer (actor-based) | D2 | A |
| N10 | correlation_id + audit plumbing | — | A |

---

## DEFERRED — explicitly out of v1

| Item | Reason | Class |
|---|---|---|
| FastAPI bridge / transport | **Not on the RM critical path** — thesis provable in-process (audit §H.2) | D |
| MCP transport | Transport ≠ architecture; nothing to integrate yet | D |
| OpenClaw / Hermes / Cursor runtime integration | No RM workflows exist to consume yet | D |
| Tier 3 execute tools (`create_task`, `update_stage`, …) | Contract only; no implementation | D |
| Production Salesforce | Sandbox at Phase 5 earliest; no credentials present | D |
| Episodic-memory persistence | Shadow-CRM risk (D6) | D |
| Neo4j migration, `service_catalog.json`, website ingestion, `website-data-health` | §20 | D |
| Client Portal / Mobile / Meta agents | §20 | D |
| L5 human-usefulness measurement | Pilot-time | D |

---

## HUMAN DECISION — blocking

| ID | Question | Default if unanswered | Blocks |
|---|---|---|---|
| **D1** | Opportunity stage taxonomy, aging thresholds, conversion-risk formula | Documented provisional B2B default | N1, N5 |
| **D2** | RM identity + visibility scoping source | Fixture `rm_id`; RM sees only assigned clients | N2, N9 |
| **D3** | `get_rm_client_context` wraps or replaces `client-lookup`? | **Wrap** (preserves gated baseline) | N2 |
| **D4** | Recommendations deterministic or LLM? | **Deterministic heuristics + structured evidence** | N5, N6 |
| **D5** | Is an LLM in v1 scope? | **No** for core; optional flag | N5 |
| **D6** | Episodic memory: defer or re-scope as audit log? | **Defer**; Working memory only | N10 |
| **D7** | Branch base | `5624803` (main + plan doc) — **taken** | — |
| **D8** | Does the §14 refactor extend to `src/tools/`? | **Yes** | R2 |

> **D1, D2, D4, D6** hit §23 stop conditions (domain ambiguity, authorization, evaluation
> semantics, platform-shaping architecture). No implementation past Phase 0 without answers or
> explicit approval of the defaults.

---

## Critical-path summary

The RM Co-pilot is **not blocked by infrastructure**. It is blocked by:

1. **N1** — the opportunity domain model (does not exist anywhere), and
2. **R1–R3** — the triplicated business logic, which would otherwise let the RM see different
   answers from different surfaces.

Everything else (bridge, MCP, runtimes, Salesforce) is deferrable without weakening the thesis.
