# AI-Native Professional Services Architecture

> A complete 6-layer architecture specification for building an AI-native corporate service provider — from knowledge graph to agent orchestration to governance.

---

## What This Is

This repository contains the **full technical blueprint** for transforming a traditional professional services firm (corporate formation, compliance, banking introductions) into an AI-native operating system. Every document is designed to be machine-readable by AI agents and human-reviewable by stakeholders.

**Key insight**: Corporate services require **graph-based reasoning** (ownership chains, jurisdiction rules, conflict-of-interest paths) that flat vector search cannot handle. This architecture is built around GraphRAG as the knowledge foundation.

---

## Command Center UI (L6 Interaction Surface)

A polished Streamlit interface that makes the whole system legible at a glance:

- **Capability gallery** — see exactly what the system can do (jurisdiction comparison, sanctions/KYC, UBO chains, drafting, renewals, onboarding briefs) and load an example with one click.
- **Live agent roster** — watch each agent's status update in real time (`idle → queued → thinking → working → done`).
- **Streaming pipeline** — every request is streamed step-by-step through the Orchestrator → specialist → Executive Assistant flow.
- **Activity log** — a persistent, timestamped history of everything that happened.

```bash
pip install -r requirements.txt
streamlit run src/app.py
```

It runs **out-of-the-box with no API key** (deterministic simulation engine in `src/engine.py`). Set `ANTHROPIC_API_KEY` and flip the **⚡ Live AI synthesis** toggle to stream the Executive Assistant's brief from a real Claude model.

---

## Runnable Skills & the Enforced Eval Gate

Every L4 skill has a **runnable reference implementation** in `src/skills/` and a
machine-enforced test suite in `L4_Skills/evals/`. The implementations are
deterministic and dependency-free (they run against in-repo fixtures instead of
live Neo4j / CRM / sanctions feeds), so the whole system executes anywhere and
the eval gate is reproducible.

```bash
python run_evals.py            # run all 9 suites, enforce the gate (exit≠0 on failure)
python run_evals.py --skill sanctions-screen
python run_evals.py --write    # persist current_score + last_run_date into each eval
```

The gate enforces **Design Principle #4** two ways:

1. **Coverage** — each skill's `EVAL_*.json` must have **≥ 10 test cases**.
2. **Pass rate** — each suite must meet its own `minimum_pass_rate` (0.90–1.00).

If either check fails for any skill, the runner exits non-zero. The same command
runs in CI on every push and pull request
([`.github/workflows/eval-gate.yml`](.github/workflows/eval-gate.yml)), so no
skill can regress below its bar and merge. Current status: **9/9 skills · 94/94
cases · gate green.**

| Skill | Cases | Min pass rate |
|---|---|---|
| `intent-classifier` | 12 | 0.95 |
| `client-lookup` | 12 | 0.95 |
| `sanctions-screen` | 10 | 1.00 |
| `conflict-check` | 10 | 0.95 |
| `ubo-chain-traverse` | 10 | 0.95 |
| `jurisdiction-compare` | 10 | 0.90 |
| `doc-expiry-scan` | 10 | 0.98 |
| `doc-draft-banking-intro` | 10 | 0.90 |
| `doc-draft-engagement-letter` | 10 | 0.90 |

---

## Architecture Layers

```
┌─────────────────────────────────────────────────┐
│  L6  Interaction Surface       (UX / Channels)  │
├─────────────────────────────────────────────────┤
│  L5  Agent Layer         (Orchestrator + Agents) │
├─────────────────────────────────────────────────┤
│  L4  Skill & Workflow Layer    (Skills + Evals)  │
├─────────────────────────────────────────────────┤
│  L3  Integration & Tool Layer  (APIs + MCP)      │
├─────────────────────────────────────────────────┤
│  L2  Memory & Context Layer    (4 Memory Types)  │
├─────────────────────────────────────────────────┤
│  L1  Knowledge Foundation      (GraphRAG)        │
└─────────────────────────────────────────────────┘
```

---

## Repository Structure

```
.
├── L1_Knowledge_Foundation/          # GraphRAG — the critical base layer
│   ├── GRAPH_SCHEMA.md               #   Entity types, relationships, query patterns
│   ├── CORPUS_INDEX.md               #   Document source inventory (10 sources)
│   └── GRAPHRAG_INDEXING_PIPELINE.md #   6-stage pipeline: ingest → extract → resolve → load → embed → validate
│
├── L2_Memory/                        # 4 memory types with schemas and retention rules
│   ├── MEMORY_SCHEMA.md              #   Episodic, Semantic, Procedural, Working memory specs
│   ├── Semantic Memory.json          #   Sample semantic memory structure
│   ├── Procedural Memory.json        #   Sample procedural memory structure
│   └── Working Memory.json           #   Sample working memory structure
│
├── L3_Tools/                         # Tool registry and governance
│   └── TOOL_REGISTRY.md             #   7 tools registered: GraphRAG, CRM, Drive, Web, Sanctions, Calendar, Registry
│
├── L4_Skills/                        # Atomic, testable capabilities (9 skills)
│   ├── SKILL_intent-classifier.md    #   + client-lookup, sanctions-screen, conflict-check,
│   ├── SKILL_*.md                    #     ubo-chain-traverse, jurisdiction-compare, doc-expiry-scan,
│   ├── WORKFLOW_client-onboarding.md #     doc-draft-engagement-letter, doc-draft-banking-intro
│   └── evals/                        #   EVAL_<skill>.json per skill (≥10 cases, per-suite pass gate)
│
├── src/                              # Runnable implementation
│   ├── app.py / engine.py            #   L6 Command Center (Streamlit) + simulation engine
│   ├── agents.py / tasks.py / tools/ #   CrewAI crew scaffold
│   ├── skills/                       #   Deterministic reference implementation of all 9 L4 skills
│   └── evals/                        #   Generic matcher + eval-gate runner
├── run_evals.py                      # Enforced eval gate (also runs in CI)
│
├── L5_Agents/                        # Named agents with defined roles and permissions
│   ├── AGENT_SPEC_Orchestrator.md    #   Central router — classifies intent, dispatches to specialists
│   ├── AGENT_SPEC_Research.md        #   Jurisdiction comparisons, regulatory lookups
│   ├── AGENT_SPEC_Compliance.md      #   UBO traversal, sanctions screening, conflict checks
│   ├── AGENT_SPEC_Drafting.md        #   Engagement letters, banking intros
│   ├── AGENT_SPEC_Operations.md      #   Internal alerts, CRM sync
│   └── AGENT_SPEC_ExecutiveAssistant.md # Command Center for human executive
│
├── L6_Interaction/                   # UX spec (internal chat) + Command Center (src/app.py)
│
├── governance/                       # Cross-cutting policies
│   └── GOVERNANCE.md                #   Approval matrix, change management, incident response, audit, data retention
│
└── reference/                        # Source materials
    ├── AI_Native_Architecture_Workbook.xlsx   # Original master workbook (8 sheets)
    ├── excel_content.md                       # Extracted workbook content (text)
    └── read_excel.py                          # Utility script
```

---

## Build Roadmap

| Phase | Timeline | Deliverables | Status |
|---|---|---|---|
| **Phase 0 — Foundation** | Weeks 1–2 | L1 GraphRAG Schema + Corpus + Pipeline, L2 Memory Schema | ✅ DONE |
| **Phase 1 — Agent Skeleton** | Weeks 3–4 | L3 Tool Registry, L5 Orchestrator + Research + Compliance Agents | ✅ DONE |
| **Phase 2 — First Skills** | Weeks 5–6 | L4 intent-classifier, client-lookup (+ evals) | ✅ DONE |
| **Phase 3 — Workflows** | Weeks 7–10 | Client onboarding workflow, all 9 skills + agents, **runnable impls + enforced eval gate** | ✅ DONE |
| **Phase 4 — Surface & Governance** | Weeks 11–12 | L6 UX Spec + Command Center, Governance, Department OS Map | ✅ DONE |

> All 9 L4 skills ship with a runnable reference implementation (`src/skills/`) and a
> CI-enforced eval gate (`run_evals.py` — **94/94 cases, gate green**). See
> [Runnable Skills & the Enforced Eval Gate](#runnable-skills--the-enforced-eval-gate).

---

## Key Design Principles

1. **Graph-first retrieval** — Ownership chains, jurisdiction rules, and conflict paths are traversed via Cypher, not vector search.
2. **Human-in-the-loop by default** — Every compliance output and client-facing document requires human approval before action.
3. **No autonomous client communication** — Agents draft; humans review and send.
4. **Eval-gated deployment** — No skill or agent goes live without ≥90% pass rate on its EVAL.json test suite.
5. **Immutable audit trails** — Compliance checks, overrides, and routing decisions are logged permanently.

---

## Agents

| Agent | Risk Level | Primary Skills |
|---|---|---|
| **Orchestrator** | LOW | `intent-classifier`, `client-lookup` |
| **Research Agent** | MEDIUM | `jurisdiction-compare`, `regulation-lookup`, `entity-eligibility-check` |
| **Compliance Agent** | HIGH | `ubo-chain-traverse`, `sanctions-screen`, `conflict-check`, `doc-expiry-scan` |
| **Drafting Agent** | MEDIUM-HIGH | `doc-draft-engagement`, `doc-draft-banking-intro`, `structure-chart-gen` |
| **Operations Agent** | MEDIUM | `mandate-renewal-alert`, `deadline-tracker`, `report-assembly` |
| **Executive Assistant** | HIGH | Acts as the Command Center, orchestrates all sub-agents, synthesizes exec briefs, manages meetings |

---

## Technology Stack

| Component | Technology |
|---|---|
| Graph Database | Neo4j (Aura) |
| Vector Store | Pinecone / Weaviate |
| Embedding Model | OpenAI `text-embedding-3-small` |
| Pipeline Orchestration | Apache Airflow / Prefect |
| CRM | Salesforce (MCP Server) |
| Document Parsing | unstructured.io / Apache Tika |
| NER / Extraction | LLM-based (structured output) |

---

## Contributing

This is an internal architecture repository. All changes must follow the **Change Management Process** defined in [`governance/GOVERNANCE.md`](governance/GOVERNANCE.md):

1. Submit a Change Request with scope, rationale, and rollback plan.
2. Changes to L4/L5 require EVAL.json pass rate ≥ 90%.
3. Schema changes (L1) require AI Lead + Data Lead approval.

---

## License

Internal use only. Not for public distribution.
