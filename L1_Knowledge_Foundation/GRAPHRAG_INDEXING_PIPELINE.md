# GraphRAG Indexing Pipeline — L1 Technical Specification

**Version**: 1.0.0
**Status**: DRAFT
**Created**: 2026-04-29
**Owner**: Engineering / Data Team
**Layer**: L1 — Knowledge Foundation
**Roadmap Ref**: Deliverable #3 — Phase 0 (Foundation, Weeks 1–2)
**Blocks**: Research Agent, Compliance Agent, all skills that query the knowledge graph

> This document specifies how raw data from the 10 corpus sources defined in `CORPUS_INDEX.md` is ingested, transformed, and loaded into the entity + relationship graph defined in `GRAPH_SCHEMA.md`.

---

## 1. Pipeline Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     SOURCE LAYER (10 sources)                    │
│  CRM · KYC · BVI Reg · Cayman Reg · ACRA · FATF · EU UBO ·     │
│  DMS · News Feeds · Bank Guidelines                             │
└──────────────┬───────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   STAGE 1: INGESTION                             │
│  API Pull / Webhook / Manual Upload → Raw Data Store             │
│  Format normalisation · Deduplication · Provenance tagging       │
└──────────────┬───────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   STAGE 2: EXTRACTION                            │
│  Entity Recognition · Relationship Extraction · Property Parse   │
│  Schema validation against GRAPH_SCHEMA.md                       │
└──────────────┬───────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   STAGE 3: RESOLUTION                            │
│  Entity Deduplication · Cross-source Merge · Conflict Detection  │
│  Golden Record selection (Registry > CRM > DMS > PDF)            │
└──────────────┬───────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   STAGE 4: GRAPH LOAD                            │
│  Upsert nodes · Upsert edges · Version stamp · Audit log        │
│  Target: Neo4j (primary) / NetworkX (dev/test)                   │
└──────────────┬───────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   STAGE 5: EMBEDDING & INDEX                     │
│  Chunk unstructured docs · Embed with text-embedding-3-small     │
│  Store in vector index · Link chunks to graph nodes              │
└──────────────┬───────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   STAGE 6: VALIDATION & MONITORING               │
│  Schema conformance check · Stale detection · Quality scoring    │
│  Dashboard update (07_Dashboard)                                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Stage 1 — Ingestion

### 2.1 Ingestion Methods per Source

| Source | Method | Trigger | Raw Format | Landing Zone |
|---|---|---|---|---|
| Salesforce CRM | REST API pull (bulk) | Cron: `0 2 * * *` (daily 2am UTC) | JSON | `raw/crm/YYYY-MM-DD/` |
| KYC / AML System | REST API (real-time) | Event-driven (new profile / flag update) | JSON | `raw/kyc/` |
| BVI Registry API | REST API pull | Cron: `0 3 * * 1` (Monday 3am) | JSON | `raw/registry/bvi/` |
| Cayman Registry API | REST API pull | Cron: `0 3 * * 2` (Tuesday 3am) | JSON | `raw/registry/cayman/` |
| Singapore ACRA | REST API pull | Cron: `0 4 * * 1-5` (weekdays 4am) | JSON | `raw/registry/sg/` |
| FATF Publications | Manual download | Quarterly (manual trigger) | PDF | `raw/fatf/` |
| EU UBO Register | REST API (limited) | Cron: `0 5 1 * *` (1st of month) | JSON | `raw/eu_ubo/` |
| DMS (Google Drive) | Webhook (on upload) | Real-time | PDF / DOCX | `raw/dms/` |
| Regulatory News | RSS / stream | Continuous | XML / JSON | `raw/news/` |
| Bank Guidelines | Manual upload | Annual / on change | PDF | `raw/bank_guides/` |

### 2.2 Raw Data Store Rules
- All ingested data is written to a time-partitioned landing zone before processing.
- No raw data is deleted — every ingestion batch is retained for 90 days for replay/debugging.
- Each record is tagged with: `source_id`, `ingestion_timestamp`, `batch_id`, `file_hash`.

### 2.3 Deduplication at Ingestion
- If the `file_hash` of an incoming document matches an existing record, skip re-processing.
- For API sources, deduplication is by `uniqueness_key` as defined in `GRAPH_SCHEMA.md` (e.g., `client_id`, `individual_id`).

---

## 3. Stage 2 — Extraction

### 3.1 Structured Sources (API / JSON)

For CRM, KYC, Registry APIs, and ACRA:
1. Parse JSON response against the expected schema.
2. Map fields to entity properties per `GRAPH_SCHEMA.md`.
3. Extract implicit relationships (e.g., a CRM record linking a Client to a Service_Mandate implies a `HAS_MANDATE` edge).
4. Validate all required properties are present. If missing, log to `extraction_errors.log` and skip the record (do not create incomplete nodes).

### 3.2 Unstructured Sources (PDF / DOCX)

For FATF, DMS uploads, Bank Guidelines:
1. **OCR / Text Extraction**: Use a document parser (e.g., `unstructured.io` or `Apache Tika`) to extract raw text.
2. **Section Splitting**: Split by heading/section markers.
3. **Entity Recognition**: Apply an LLM-based NER pass to extract:
   - Entity mentions (names, jurisdiction codes, registration numbers)
   - Relationship signals ("is a director of", "owns 40% of", "incorporated in")
   - Date extraction (incorporation dates, expiry dates)
4. **Schema Mapping**: Map extracted entities to `GRAPH_SCHEMA.md` entity types. If a new entity type is detected that is not in the schema, log it as `schema_gap` — do not create it.
5. **Confidence Tagging**: Each extracted entity/relationship receives a confidence score (0.0–1.0). Below 0.7 → routed to human review queue.

### 3.3 Chunking Parameters (for Vector Embedding)

| Source Type | Chunk Size (tokens) | Overlap (tokens) | Splitting Strategy |
|---|---|---|---|
| PDF / DOCX (DMS) | 512 | 64 | Paragraph boundaries |
| FATF PDFs | 1024 | 128 | Section headers |
| News feeds | 256 | 32 | Article boundaries |
| Bank guidelines | 512 | 64 | Section headers |

---

## 4. Stage 3 — Entity Resolution

### 4.1 Cross-Source Merge Logic

The same real-world entity may appear in multiple sources with slightly different data. The resolution engine applies:

1. **Exact Key Match**: If two records share the same `uniqueness_key` (e.g., `client_id`), merge them.
2. **Fuzzy Name Match**: If no key match, apply fuzzy string matching (Jaro-Winkler, threshold ≥ 0.85) on name fields within the same entity type.
3. **Contextual Match**: For Individuals, cross-check `date_of_birth` + `nationality` as secondary confirmation.

### 4.2 Golden Record Priority

When conflicting values exist for the same property, select the authoritative source:

```
Registry API  >  KYC System  >  CRM  >  DMS  >  PDF Upload  >  News Feed
```

- The winning value is stored as the primary property.
- Losing values are stored in a `source_variants` array for audit.
- All merge decisions are logged to `entity_resolution_log`.

### 4.3 Conflict Escalation
- If two HIGH-priority sources (Registry vs KYC) disagree on a critical field (e.g., `risk_rating`, `sanction_flag`), the record is flagged for **human review** and blocked from the graph until resolved.
- Conflicts on non-critical fields (e.g., `trade_name`, `address`) are auto-resolved using the priority order above and logged.

---

## 5. Stage 4 — Graph Load

### 5.1 Target Database
- **Production**: Neo4j (Aura or self-hosted) — optimised for multi-hop traversal queries (OWNS chains, conflict paths).
- **Development / Test**: NetworkX (Python in-memory) — for rapid iteration and unit testing of query patterns.

### 5.2 Load Strategy

| Operation | Method | Idempotency |
|---|---|---|
| New node | `MERGE` on uniqueness key | Yes — will not duplicate |
| Update node properties | `SET` on matched node | Yes — overwrites with latest |
| New relationship | `MERGE` on from + to + type | Yes — will not duplicate |
| Update relationship properties | `SET` on matched edge | Yes — overwrites with latest |
| Delete node | Soft-delete: `SET status = 'archived'` | Never hard-delete from graph |

### 5.3 Version Stamping
Every node and edge receives:
- `_created_at`: ISO 8601 timestamp of first creation.
- `_updated_at`: ISO 8601 timestamp of last modification.
- `_source_batch_id`: Reference to the ingestion batch that last touched this record.
- `_source_id`: Which corpus source provided this data.

### 5.4 Load Audit
Every graph load operation writes to `graph_load_audit.log`:
```json
{
  "batch_id": "string",
  "timestamp": "ISO 8601",
  "nodes_created": 0,
  "nodes_updated": 0,
  "edges_created": 0,
  "edges_updated": 0,
  "errors": 0,
  "error_details": [],
  "duration_seconds": 0
}
```

---

## 6. Stage 5 — Embedding & Vector Index

### 6.1 What Gets Embedded
Only **unstructured content** is embedded. Structured data (CRM, KYC, Registry) lives as graph nodes and is queried via Cypher — not vector search.

| Content Type | Embedding Model | Vector Store | Dimension |
|---|---|---|---|
| DMS documents (chunks) | `text-embedding-3-small` | Pinecone / Weaviate | 1536 |
| FATF publication sections | `text-embedding-3-small` | Pinecone / Weaviate | 1536 |
| News summaries | `text-embedding-3-small` | Pinecone / Weaviate | 1536 |
| Bank guidelines (chunks) | `text-embedding-3-small` | Pinecone / Weaviate | 1536 |

### 6.2 Graph–Vector Linking
Every vector chunk stores metadata linking it back to the graph:
```json
{
  "chunk_id": "string",
  "doc_id": "string (maps to Document entity in graph)",
  "source_id": "string",
  "entity_refs": ["entity_id_1", "entity_id_2"],
  "jurisdiction_scope": "string",
  "chunk_text": "string",
  "embedding": [0.012, -0.034, ...]
}
```

This enables **hybrid retrieval**: Cypher query finds relevant entities → vector search retrieves supporting document chunks → combined response.

---

## 7. Stage 6 — Validation & Monitoring

### 7.1 Post-Load Validation Checks

| Check | Method | Fail Action |
|---|---|---|
| Schema conformance | Every node validated against `GRAPH_SCHEMA.md` JSON Schema | Quarantine node; log error |
| Orphan detection | Find nodes with zero relationships | Flag for review (may be valid new entities) |
| Stale detection | Compare `_updated_at` against source's `stale_threshold` (per `CORPUS_INDEX.md`) | Add `stale_flag: true`; alert source owner |
| Duplicate detection | Find nodes with same `full_legal_name` + `jurisdiction` but different IDs | Route to entity resolution queue |
| Relationship integrity | Validate all edges connect valid node types per schema | Delete invalid edge; log error |

### 7.2 Quality Metrics (tracked per batch)

| Metric | Target | Alert Threshold |
|---|---|---|
| Entity extraction accuracy | ≥ 90% | < 85% |
| Relationship extraction accuracy | ≥ 85% | < 80% |
| Schema validation pass rate | 100% | < 98% |
| Stale entity percentage | < 5% | > 10% |
| Duplicate rate (post-resolution) | < 1% | > 3% |
| Average ingestion-to-graph latency | < 30 min (API sources) | > 60 min |

### 7.3 Dashboard Integration
After each pipeline run, update the `07_Dashboard` sheet with:
- Total nodes / edges in graph
- Nodes added / updated / quarantined this batch
- Source freshness status (per `CORPUS_INDEX.md` stale thresholds)
- Quality score trend

---

## 8. Operational Runbook

### 8.1 Daily Operations
1. **02:00 UTC** — CRM sync runs. Monitor `graph_load_audit.log` for errors.
2. **03:00–04:00 UTC** — Registry syncs (BVI Mon, Cayman Tue, ACRA weekdays). Check for rate-limit warnings.
3. **Throughout day** — DMS webhook fires on new uploads. Spot-check `extraction_errors.log`.
4. **End of day** — Review stale detection report. Escalate any source past its threshold.

### 8.2 Weekly Operations
1. Run full orphan detection scan.
2. Review entity resolution queue (fuzzy matches flagged for human confirmation).
3. Check embedding index size and vector store health.
4. Update `CORPUS_INDEX.md` Section 4 (Update Cadence) with latest run statuses.

### 8.3 Quarterly Operations
1. FATF publications ingestion (manual download + pipeline run).
2. Full schema conformance audit across all nodes.
3. Review and update quality score thresholds.
4. Evaluate whether new corpus sources should be added (per `CORPUS_INDEX.md` Section 5 — Gaps).

### 8.4 Failure Recovery

| Failure Scenario | Recovery Action | RTO |
|---|---|---|
| API source returns errors | Retry 3x with exponential backoff (1m, 5m, 15m). If still failing, skip source, set `stale_flag`, alert owner. | < 30 min |
| Graph database unavailable | Queue all load operations. Replay from raw store once DB recovers. | < 2 hours |
| Vector store unavailable | Agents fall back to graph-only queries (degraded mode — flag to user). | < 1 hour |
| Extraction produces > 10% error rate | Halt pipeline for that source. Alert Data Engineer. Do not load bad data. | Immediate halt |
| Entity resolution conflict (HIGH-priority sources) | Block affected records. Route to human review queue. | < 24 hours |

---

## 9. Security & Access Control

| Role | Pipeline Access | Graph Access |
|---|---|---|
| Data Engineer | Full pipeline admin (run, configure, debug) | Graph WRITE (via pipeline only — no direct edits) |
| AI Lead | Pipeline monitoring (read-only) | Graph ADMIN (schema changes via Change Request) |
| Agents (all) | No pipeline access | Graph READ only (via GraphRAG Query Engine) |
| Compliance Officer | Pipeline audit logs (read-only) | Graph READ (deep traversal for compliance checks) |

- No agent may write directly to the graph. All mutations flow through this pipeline.
- Schema changes require approval per `GOVERNANCE.md` Section 2, Row 8.
- All pipeline credentials stored in a secrets manager (not in code or config files).

---

## 10. Technology Stack Summary

| Component | Technology | Rationale |
|---|---|---|
| Orchestration | Apache Airflow / Prefect | DAG-based scheduling, retry logic, monitoring |
| Graph Database | Neo4j (Aura) | Native graph traversal, Cypher query language, mature ecosystem |
| Vector Store | Pinecone / Weaviate | Managed service, metadata filtering, scalable |
| Embedding Model | OpenAI `text-embedding-3-small` | Cost-effective, 1536-dim, proven quality |
| Document Parsing | `unstructured.io` / Apache Tika | Handles PDF, DOCX, OCR out of the box |
| NER / Extraction | LLM-based (GPT-4o / Claude) with structured output | Higher accuracy than rule-based NER for legal/corporate docs |
| Raw Data Store | Cloud object storage (S3 / GCS) | Cheap, durable, versioned |
| Monitoring | Grafana + custom dashboards | Real-time pipeline health visibility |

---

## 11. Cross-References

| Document | Relationship |
|---|---|
| `GRAPH_SCHEMA.md` | Defines the target schema this pipeline populates |
| `CORPUS_INDEX.md` | Defines the source inventory this pipeline ingests from |
| `TOOL_REGISTRY.md` | GraphRAG Query Engine (Tool #1) reads from the graph this pipeline builds |
| `MEMORY_SCHEMA.md` | Semantic Memory feeds from the same corpus; must not duplicate |
| `GOVERNANCE.md` | Schema changes require approval (Section 2, Row 8); audit requirements (Section 5) |
| `AGENT_SPEC_Research.md` | Primary consumer — uses GraphRAG for jurisdiction + regulatory queries |
| `AGENT_SPEC_Compliance.md` | Critical consumer — uses GraphRAG for UBO traversal, conflict detection |
