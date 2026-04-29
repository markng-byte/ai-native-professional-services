# AI-Native Professional Services Architecture

> A complete 6-layer architecture specification for building an AI-native corporate service provider — from knowledge graph to agent orchestration to governance.

---

## What This Is

This repository contains the **full technical blueprint** for transforming a traditional professional services firm (corporate formation, compliance, banking introductions) into an AI-native operating system. Every document is designed to be machine-readable by AI agents and human-reviewable by stakeholders.

**Key insight**: Corporate services require **graph-based reasoning** (ownership chains, jurisdiction rules, conflict-of-interest paths) that flat vector search cannot handle. This architecture is built around GraphRAG as the knowledge foundation.

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
├── L4_Skills/                        # Atomic, testable capabilities
│   ├── SKILL_intent-classifier.md    #   Routes inbound messages to the correct agent
│   ├── SKILL_client-lookup.md        #   Retrieves client profile + mandates + history
│   └── evals/                        #   Test cases per skill (≥10 cases, ≥90% pass rate required)
│       ├── EVAL_intent-classifier.json
│       └── EVAL_client-lookup.json
│
├── L5_Agents/                        # Named agents with defined roles and permissions
│   ├── AGENT_SPEC_Orchestrator.md    #   Central router — classifies intent, dispatches to specialists
│   ├── AGENT_SPEC_Research.md        #   Jurisdiction comparisons, regulatory lookups
│   └── AGENT_SPEC_Compliance.md      #   UBO traversal, sanctions screening, conflict checks
│
├── L6_Interaction/                   # UX specs per channel (TODO)
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
| **Phase 0 — Foundation** | Weeks 1–2 | L1 GraphRAG Schema + Corpus + Pipeline, L2 Memory Schema | ✅ DRAFTED |
| **Phase 1 — Agent Skeleton** | Weeks 3–4 | L3 Tool Registry, L5 Orchestrator + Research + Compliance Agents | ✅ DRAFTED |
| **Phase 2 — First Skills** | Weeks 5–6 | L4 intent-classifier, client-lookup (+ evals) | ✅ DRAFTED |
| **Phase 3 — Workflows** | Weeks 7–10 | Client onboarding workflow, remaining skills + agents | 🔲 TODO |
| **Phase 4 — Surface & Governance** | Weeks 11–12 | L6 UX Spec, Governance, Department OS Map | 🟡 PARTIAL |

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
