
---

## CORPUS_INDEX.md

```markdown
# Corpus Index (L1)
**Version:** 1.0  
**Status:** DRAFT – pending review  
**Last Updated:** 2026-04-29  
**Owner:** Data / Knowledge Team  

> This document lists all document sources that feed into the GraphRAG knowledge graph. Each source is described with its update frequency, jurisdiction scope, quality score, and responsible owner.  
> **Why index?** Without a corpus index, you cannot track staleness, duplication, or coverage gaps – leading to confident wrong answers.

---

## 1. Document Sources

| # | Source Name | Document Type | Jurisdiction Scope | Update Frequency | Indexing Method | Quality Score (1‑5) | Last Updated | Responsible Owner | Stale Threshold |
|---|-------------|---------------|--------------------|------------------|----------------|---------------------|--------------|--------------------|-----------------|
| 1.0 | **Salesforce CRM** | Client records, Mandate data, Officer assignments | Global – all client jurisdictions | Daily incremental | API pull → entity extraction | 4.5 | 2026-04-28 | CRM Admin | 7 days |
| 2.0 | **KYC / AML System (internal)** | Individual profiles, PEP/sanction flags, UBO declarations | All | Real‑time via API | API pull → graph node update | 5.0 | 2026-04-29 | Compliance Officer | 1 day |
| 3.0 | **BVI Registry API** | Incorporation certificates, director lists, annual filings | British Virgin Islands | Weekly (every Monday) | API → JSON → entity mapping | 4.0 | 2026-04-25 | Data Engineer | 14 days |
| 4.0 | **Cayman Islands Registry API** | Company registers, registered office info | Cayman Islands | Weekly (every Tuesday) | API → JSON → entity mapping | 4.0 | 2026-04-26 | Data Engineer | 14 days |
| 5.0 | **Singapore ACRA** | Business profiles, filing deadlines, officers | Singapore | Daily (business days) | API → structured data | 4.8 | 2026-04-29 | Data Engineer | 3 days |
| 6.0 | **FATF Publications** | Recommendations, mutual evaluation reports, high‑risk jurisdictions | Global (all) | Quarterly (March/June/Sept/Dec) | Manual download → PDF → chunking | 3.5 | 2026-03-15 | Compliance Analyst | 90 days |
| 7.0 | **EU Register of Beneficial Owners** | UBO data for EU entities | EU member states | Monthly | API pull (limited) | 3.0 | 2026-04-01 | Data Engineer | 30 days |
| 8.0 | **Internal Document Management System (DMS)** | Engagement letters, banking intro letters, client PDF uploads | Varies by client | Real‑time (webhook on upload) | Document parser → text + metadata | 4.2 | 2026-04-29 | Operations Manager | N/A (event‑driven) |
| 9.0 | **Regulatory News Feeds (e.g., Thomson Reuters)** | Compliance alerts, rule changes, jurisdiction updates | Global | Continuous (stream) | RSS → NLP summarization | 4.0 | 2026-04-29 | Compliance Analyst | 1 hour (for alerts) |
| 10.0 | **Bank Account Opening Guidelines** | PDFs from various banks (HSBC, BNP, DBS, etc.) | Per bank | Annually or on change | Manual upload → OCR → chunking | 3.0 | 2026-01-15 | Research Analyst | 365 days |

---

## 2. Corpus Quality & Governance

### 2.1 Quality Score Definition

| Score | Meaning | Action |
|-------|---------|--------|
| 5.0 | Fully structured, real‑time API, no manual steps | Monitor only |
| 4.0 – 4.9 | Mostly reliable, small delays or minor parsing issues | Weekly sanity check |
| 3.0 – 3.9 | Partial coverage, manual intervention required | Monthly review; consider replacement |
| < 3.0 | Unreliable or stale | Flag in agent outputs; do not use for critical decisions |

### 2.2 Deduplication Strategy

When the same entity (e.g., a client) appears in multiple sources:
- **Prefer**: Registry API > CRM > DMS > PDF upload
- **Conflicts** are logged to `duplicate_resolution_log.csv` and require manual review if the impact is HIGH.

### 2.3 Stale Detection

Every source has a `stale_threshold` (see table). If a source is not updated within that window, the system:
- Adds a `stale_flag: true` to all entities from that source.
- Agents receive a warning: *“Information from [source] may be out of date. Last updated X days ago.”*
- Alerts the responsible owner via email (daily summary).

---

## 3. Indexing Pipeline Parameters

| Source | Indexing Method | Chunk Size (tokens) | Overlap | Embedding Model | Graph Integration |
|--------|----------------|----------------------|---------|-----------------|-------------------|
| CRM | Entity mapping → graph nodes | N/A | N/A | N/A | Direct node/edge creation |
| KYC system | API → node update | N/A | N/A | N/A | Node properties |
| Registry APIs | JSON → node + relationship | N/A | N/A | N/A | Entity + registration edges |
| PDF/DOCX (DMS) | OCR + text extraction | 512 | 64 | `text-embedding-3-small` | Attach as RELATED_DOCUMENT |
| FATF PDFs | Section splitting | 1024 | 128 | `text-embedding-3-small` | Link to Jurisdiction + Regulator |
| News feeds | Summarize then chunk | 256 | 32 | `text-embedding-3-small` | Event nodes + timestamp |

---

## 4. Update Cadence (Automated Schedule)

| Source | Cron / Trigger | Last Run Status | Next Run |
|--------|----------------|----------------|----------|
| Salesforce CRM | `0 2 * * *` (daily 2am UTC) | ✅ Success | 2026-04-30 02:00 |
| BVI Registry | `0 3 * * 1` (Monday 3am) | ⚠️ Partial (rate limit) | 2026-05-04 03:00 |
| Cayman Registry | `0 3 * * 2` (Tuesday 3am) | ✅ Success | 2026-05-05 03:00 |
| ACRA (Singapore) | `0 4 * * 1-5` (weekdays 4am) | ✅ Success | 2026-04-30 04:00 |
| DMS webhook | Real‑time | N/A | Always on |
| FATF PDFs | Manual (quarterly) | Last: 2026-03-15 | Next: 2026-06-15 |

---

## 5. Missing Sources (Gaps to Fill)

From the canonical query patterns, the following sources are **not yet indexed** but required:

- **EU register of beneficial owners** – partially done (score 3.0). Need full API integration.
- **Bank success rate data** – not currently captured. Should be derived from historic mandates in CRM.
- **Conflict of interest declarations** – stored in free‑text emails; need extraction pipeline.

**Action items**:
1. Upgrade EU UBO API integration by 2026-05-15.
2. Build ETL to compute bank success rates from CRM mandate history by 2026-06-01.
3. Design conflict extraction from email corpus by 2026-07-01.

---

## 6. Owner Responsibilities

| Role | Responsibilities |
|------|------------------|
| **Data Engineer** | Maintain API connectors, indexing pipeline, stale detection. |
| **Compliance Analyst** | Validate regulatory sources, update FATF/jurisdiction feeds. |
| **Operations Manager** | Ensure DMS uploads trigger webhook; clean up duplicate documents. |
| **AI Lead** | Review quality scores, approve new sources, adjust embedding models. |

---

**Author:** Manus AI (based on workbook `02_L1_GraphRAG_Spec` – Corpus Index)  
**Date:** 2026-04-29