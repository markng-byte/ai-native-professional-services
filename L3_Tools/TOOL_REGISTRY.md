# Tool Registry (L3)
**Version:** 1.0  
**Status:** DRAFT – pending review  
**Last Updated:** 2026-04-29  
**Owner:** Engineering / IT  

> Every tool an agent uses MUST be registered here before it can be called. This registry defines authentication, permissions, rate limits, and fallback behavior.  
> **Review cadence:** Monthly audit – next audit: 2026-05-29.

---

## 1. Registered Tools

| # | Tool Name | Type | Auth Method | Agents Permitted (permission level) | Data Accessed / Written | Rate Limit / Cost | Fallback If Unavailable |
|---|-----------|------|-------------|--------------------------------------|------------------------|-------------------|-------------------------|
| 1.0 | **GraphRAG Query Engine** | Internal / Knowledge | Internal API key (per‑agent scoped) | All agents (READ) <br> Compliance Agent (READ – deep traversal) <br> AI Lead (ADMIN – schema changes) | Entity graph, relationship graph, document corpus. **NO write from agents.** | No rate limit (internal); query cost monitored | Fallback to flat vector search on document corpus (degraded – flag to user) |
| 2.0 | **Salesforce CRM** | MCP Server – CRM | OAuth 2.0, per‑agent service account | Orchestrator (READ – client lookup) <br> Operations Agent (READ/WRITE – mandate updates) <br> Compliance Agent (WRITE – risk flags only) | Client records, mandate records, contact data, risk ratings. PII present. | 500 API calls/hour per agent; excess → queue | Cache last 24h read; queue writes; alert human if write backlog > 10 |
| 3.0 | **Google Drive / Docs** | MCP Server – DMS | OAuth 2.0, service account per department | Drafting Agent (READ templates, WRITE drafts to staging folder) <br> Operations Agent (READ/WRITE reports) | Document templates, generated drafts. No CRM data written to Drive. | No meaningful rate limit at current scale | Local template cache for Drafting Agent; manual upload if Drive unavailable |
| 4.0 | **Web Search** | External API | API key (shared, monitored) | Research Agent (READ) <br> Compliance Agent (READ – regulatory news) | Public web content only. Must not be used to exfiltrate internal data. | 100 calls/hour; cost ~$0.01/call. Research Agent priority. | Return cached result with staleness warning; flag to human for time‑sensitive queries |
| 5.0 | **Sanctions List API** (e.g. Dow Jones / ComplyAdvantage) | External Compliance API | API key – compliance team owns credential | Compliance Agent (READ only) <br> **No other agent permitted** | Individual/entity names screened against sanctions, PEP, adverse media lists | Per‑screen pricing (~$0.10–0.50/screen); monthly budget cap = $5,000 | **BLOCK action** – no sanction check = no onboarding. Human must manually screen. |
| 6.0 | **Calendar / Email API** | MCP Server – Communication | OAuth 2.0, per‑officer delegated access | Operations Agent (READ calendar, WRITE draft emails to staging – **NOT send**) <br> No agent can send email directly | Calendar events, email drafts. All email sends require human approval. | Standard API limits; email sends are human‑gated so volume low | Queue calendar events; human sends email manually |
| 7.0 | **Registry APIs** (per‑jurisdiction: BVI, Cayman, SG, etc.) | External – Registries | Per‑registry credentials (varies: API key / portal login) | Research Agent (READ – entity status lookups) <br> Compliance Agent (READ – filing confirmations) | Registered entity status, officer lists, filing dates. Public data. | Varies by registry; most allow ~50–200 calls/day | Manual registry portal lookup; flag as "unverified via API" in output |

---

## 2. Governance Rules

- **New tool addition** → Requires Engineering/IT to create a registry entry and define permission matrix. Must pass security review.
- **Permission change** → Requires AI Lead + Compliance Officer (if data is PII or regulated) approval.
- **Audit trail** – Every tool call is logged with: `timestamp`, `agent_id`, `tool_name`, `response_code`, `latency_ms`.
- **Deprecation** – Tools removed from registry are blocked at the gateway level. Active agents referencing them will fail‑open with `fallback` if defined, otherwise raise escalation.

**Next audit scheduled:** 2026-05-29

**Author:** Manus AI (based on workbook `05_L2L3_Memory_Tools` – L3 Tool Registry)  
**Date:** 2026-04-29