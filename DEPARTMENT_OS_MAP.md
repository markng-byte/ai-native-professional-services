# Department OS Map — v1.0

**Version**: 1.0.0
**Status**: DRAFT
**Layer**: Cross-cutting (L1–L6)
**Created**: 2026-04-29
**Owner**: AI Lead / Chief of Staff
**Review Cadence**: Quarterly
**Roadmap Ref**: Deliverable #19 — Phase 4 (Weeks 11–12)

> This is the master index linking all architecture layers, documents, agents, skills, and workflows. It serves as the single source of truth for "what exists" in the AI-Native system.

---

## 1. Architecture Inventory Summary

| Metric | Count |
|---|---|
| Total Layers | 6 + Cross-cutting |
| Total Documents | 31+ |
| Agents Defined | 6 |
| Skills Defined | 14 |
| Workflows Defined | 1 |
| Eval Suites | 9 |
| Tools Registered | 7 |

---

## 2. Layer-by-Layer Inventory

### L1 — Knowledge Foundation (GraphRAG)

| Document | Status | Owner | Key Content |
|---|---|---|---|
| `GRAPH_SCHEMA.md` | DRAFT | Data / Knowledge | 10 entity types, 10 relationship types, 7 canonical query patterns |
| `CORPUS_INDEX.md` | DRAFT | Data / Knowledge | 10 document sources, quality scores, stale detection rules |
| `GRAPHRAG_INDEXING_PIPELINE.md` | DRAFT | Engineering | 6-stage pipeline: ingest → extract → resolve → load → embed → validate |

**Open Gaps**: EU UBO Register integration (score 3.0), bank success rate ETL, conflict extraction from email corpus.

---

### L2 — Memory & Context

| Document | Status | Owner | Key Content |
|---|---|---|---|
| `MEMORY_SCHEMA.md` | DRAFT | AI / Engineering | 4 memory types defined with schemas and retention |
| `Semantic Memory.json` | DRAFT | AI / Engineering | Sample structure |
| `Procedural Memory.json` | DRAFT | AI / Engineering | Sample structure |
| `Working Memory.json` | DRAFT | AI / Engineering | Sample structure |

**Open Gaps**: Episodic Memory sample not yet created. PII masking implementation not yet specified.

---

### L3 — Integration & Tool Governance

| Document | Status | Owner | Key Content |
|---|---|---|---|
| `TOOL_REGISTRY.md` | DRAFT | Engineering / IT | 7 tools registered with permissions, auth, and fallbacks |

**Open Gaps**: None — all 7 tools from the workbook are registered.

---

### L4 — Skill & Workflow Layer

#### Skills

| Skill | Agent Owner | Type | Eval Suite | Status |
|---|---|---|---|---|
| `intent-classifier` | Orchestrator | Routing | ✅ 12 test cases | DRAFT |
| `client-lookup` | Orchestrator | Data | ✅ 12 test cases | DRAFT |
| `jurisdiction-compare` | Research Agent | Research | ✅ 10 test cases | DRAFT |
| `sanctions-screen` | Compliance Agent | Compliance | ✅ 10 test cases (100% required) | DRAFT |
| `ubo-chain-traverse` | Compliance Agent | Compliance | ✅ 10 test cases | DRAFT |
| `conflict-check` | Compliance Agent | Compliance | ✅ 8 test cases | DRAFT |
| `doc-expiry-scan` | Compliance Agent | Compliance | ✅ 8 test cases | DRAFT |
| `doc-draft-engagement-letter` | Drafting Agent | Document | ✅ 6 test cases | DRAFT |
| `doc-draft-banking-intro` | Drafting Agent | Document | ✅ 6 test cases | DRAFT |
| `regulation-lookup` | Research Agent | Research | ❌ Not yet created | TODO |
| `entity-eligibility-check` | Research Agent | Research | ❌ Not yet created | TODO |
| `mandate-renewal-alert` | Operations Agent | Operations | ❌ Not yet created | TODO |
| `structure-chart-gen` | Drafting Agent | Document | ❌ Not yet created | TODO |
| `report-assembly` | Operations Agent | Operations | ❌ Not yet created | TODO |

#### Workflows

| Workflow | Status | Steps | Human Gates |
|---|---|---|---|
| `client-onboarding` | DRAFT | 9 steps across 4 agents | 7 human gates |

**Open Gaps**: 5 skills still at TODO. Additional workflows (mandate renewal, annual return) not yet specified.

---

### L5 — Agent Layer

| Agent | Risk Level | Skills Used | Spec Status |
|---|---|---|---|
| Orchestrator | LOW | `intent-classifier`, `client-lookup` | DRAFT |
| Research Agent | MEDIUM | `jurisdiction-compare`, `regulation-lookup`, `entity-eligibility-check` | DRAFT |
| Compliance Agent | HIGH | `ubo-chain-traverse`, `sanctions-screen`, `conflict-check`, `doc-expiry-scan` | DRAFT |
| Drafting Agent | MEDIUM-HIGH | `doc-draft-engagement-letter`, `doc-draft-banking-intro`, `structure-chart-gen` | DRAFT |
| Operations Agent | MEDIUM | `mandate-renewal-alert`, `deadline-tracker`, `report-assembly` | DRAFT |
| Executive Assistant | HIGH | `exec-brief`, `meeting-capture`, `drive-sync` | DRAFT |

**Open Gaps**: None — all 6 agents are specified.

---

### L6 — Interaction Surface

| Document | Status | Owner | Key Content |
|---|---|---|---|
| `UX_SPEC_internal-chat.md` | DRAFT | Product / Design | Chat UX, conversation flows, fallback behavior, role permissions |

**Open Gaps**: Client portal UX spec not yet created. Email channel spec not yet created. API endpoint spec not yet created.

---

### Cross-Cutting

| Document | Status | Owner | Key Content |
|---|---|---|---|
| `GOVERNANCE.md` | DRAFT | Legal / Compliance / AI Lead | Approval matrix, change management, incident response, data retention |
| `DEPARTMENT_OS_MAP.md` | DRAFT | AI Lead / Chief of Staff | This document — master index |

---

## 3. Agent Roster — Full Permissions Matrix

| Agent | CRM | GraphRAG | Drive | Web Search | Sanctions API | Calendar/Email | Registry APIs |
|---|---|---|---|---|---|---|---|
| Orchestrator | Read | — | — | — | — | — | — |
| Research Agent | — | Read | — | Read | — | — | Read |
| Compliance Agent | Write (flags) | Read (deep) | — | — | Read | — | Read |
| Drafting Agent | Read | Read | Read/Write | — | — | — | — |
| Operations Agent | Read/Write | Read | Read/Write | — | — | Read/Draft | — |
| Executive Assistant | — | — | Read/Write | Execute | — | Read/Write | — |

---

## 4. Roadmap Status

| # | Deliverable | Layer | Phase | Status |
|---|---|---|---|---|
| 1 | GRAPH_SCHEMA.md | L1 | Phase 0 | ✅ DRAFT |
| 2 | CORPUS_INDEX.md | L1 | Phase 0 | ✅ DRAFT |
| 3 | GraphRAG Indexing Pipeline | L1 | Phase 0 | ✅ DRAFT |
| 4 | MEMORY_SCHEMA.md | L2 | Phase 0 | ✅ DRAFT |
| 5 | TOOL_REGISTRY.md | L3 | Phase 1 | ✅ DRAFT |
| 6 | AGENT_SPEC — Orchestrator | L5 | Phase 1 | ✅ DRAFT |
| 7 | AGENT_SPEC — Research Agent | L5 | Phase 1 | ✅ DRAFT |
| 8 | AGENT_SPEC — Compliance Agent | L5 | Phase 1 | ✅ DRAFT |
| 9 | SKILL + EVAL — intent-classifier | L4 | Phase 2 | ✅ DRAFT |
| 10 | SKILL + EVAL — client-lookup | L4 | Phase 2 | ✅ DRAFT |
| 11 | SKILL + EVAL — jurisdiction-compare | L4 | Phase 2 | ✅ DRAFT |
| 12 | SKILL + EVAL — sanctions-screen | L4 | Phase 2 | ✅ DRAFT |
| 13 | WORKFLOW — client onboarding | L4 | Phase 3 | ✅ DRAFT |
| 14 | SKILL — ubo-chain-traverse, conflict-check, doc-expiry-scan | L4 | Phase 3 | ✅ DRAFT |
| 15 | SKILL — doc-draft-engagement-letter, doc-draft-banking-intro | L4 | Phase 3 | ✅ DRAFT |
| 16 | AGENT_SPEC — Drafting Agent, Operations Agent | L5 | Phase 3 | ✅ DRAFT |
| 17 | UX_SPEC — internal chat channel | L6 | Phase 4 | ✅ DRAFT |
| 18 | GOVERNANCE.md | Cross | Phase 4 | ✅ DRAFT |
| 19 | DEPARTMENT_OS_MAP.md | Cross | Phase 4 | ✅ DRAFT |
| 20 | AGENT_SPEC — Executive Assistant | L5 | Phase 4 | ✅ DRAFT |

**All 20 deliverables: COMPLETE (DRAFT status).**

---

## 5. Next Actions (Post-Draft)

| Priority | Action | Owner | Target |
|---|---|---|---|
| 1 | Review all DRAFT specs with stakeholders | AI Lead | Week 1 |
| 2 | Build remaining 5 TODO skills (regulation-lookup, entity-eligibility-check, mandate-renewal-alert, structure-chart-gen, report-assembly) | AI / Ops | Weeks 2–3 |
| 3 | Implement GraphRAG indexing pipeline (Stage 1–4) | Engineering | Weeks 2–4 |
| 4 | Deploy Neo4j instance and load initial graph | Data / Engineering | Week 3 |
| 5 | Build and run EVAL suites for Phase 2 skills | AI / QA | Week 4 |
| 6 | Promote DRAFT → ACTIVE for approved specs | AI Lead | Rolling |
