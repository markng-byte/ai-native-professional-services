# Memory Schema (L2)
**Version:** 1.0  
**Status:** DRAFT – pending review  
**Last Updated:** 2026-04-29  
**Owner:** AI / Engineering Team  

> This document defines the four memory types (episodic, semantic, procedural, working), their schemas, retention policies, PII handling rules, and agent access controls.  
> **Why four types?** Professional services need short‑term session context (working), long‑term client history (episodic), stable procedures (semantic), and performance feedback (procedural) – mixing them leads to context pollution or data leakage.

---

## 1. Memory Type Summary

| # | Memory Type | What Is Stored | Retention Policy | PII Handling | Agents With Write Access | Agents With Read Access |
|---|-------------|----------------|------------------|--------------|--------------------------|-------------------------|
| 1.0 | **Episodic** | Per‑client session history: questions, decisions, outputs, flags | Indefinite while client active; archive 2 years post‑mandate; delete on request | Mask PII fields in logs; full data in encrypted store only | Orchestrator, Compliance, Operations | Orchestrator, Compliance, Drafting, Operations |
| 2.0 | **Semantic** | Stable knowledge: jurisdiction rules, SOPs, product catalog, fee schedules | Version‑controlled; no deletion – superseded versions archived | No PII – purely procedural/regulatory | AI Lead (write after review) | All agents |
| 3.0 | **Procedural** | Skill execution patterns: step sequences, tool call patterns, failure modes | Update after every 100 skill executions or skill version change | No PII | AI Lead (write after review) | All agents |
| 4.0 | **Working** | In‑flight context: parsed intent, intermediate results, conversation turns | Ephemeral – cleared at session end or after 24h inactivity | PII permitted during session but **must be purged** at session close | All agents (during session) | All agents (during session) |

---

## 2. Detailed Schemas (JSON Schema)

### 2.1 Episodic Memory

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EpisodicMemoryEntry",
  "type": "object",
  "required": ["session_id", "client_id", "agent_id", "timestamp", "action_type", "input_summary", "output_summary", "human_approved"],
  "properties": {
    "session_id": { "type": "string", "pattern": "^ses-[a-f0-9]{16}$" },
    "client_id": { "type": "string", "pattern": "^CLI-[A-Z0-9]{8}$" },
    "agent_id": { "type": "string", "enum": ["orchestrator", "research", "drafting", "compliance", "operations"] },
    "timestamp": { "type": "string", "format": "date-time" },
    "action_type": { "type": "string", "enum": ["query", "document_generation", "compliance_check", "alert", "human_escalation"] },
    "input_summary": { "type": "string", "maxLength": 500 },
    "output_summary": { "type": "string", "maxLength": 2000 },
    "human_approved": { "type": "boolean" },
    "pii_fields_masked": { "type": "array", "items": { "type": "string" }, "default": [] }
  }
}