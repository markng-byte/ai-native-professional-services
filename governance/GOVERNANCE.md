# GOVERNANCE.md — AI-Native Enterprise Architecture

## 1. Purpose
This document defines the approval matrix, change management process, incident response procedures, audit trail requirements, AI use policy, data retention rules, and human override procedures for the AI-Native Professional Services system. It is a cross-cutting document that applies to all six architecture layers (L1–L6) and every agent, skill, tool, and workflow in the system.

**Status**: DRAFT
**Version**: 1.0.0
**Created**: 2026-04-29
**Owner**: Legal / Compliance / AI Lead
**Review Cadence**: Bi-annual + incident-driven

---

## 2. Approval Matrix

Every action produced by an AI agent must pass through a defined approval gate before it takes effect. The table below maps action types to their required approval workflow.

| # | Action Type | Risk Level | Auto-Approved? | Approver (Human) | Audit Log Required? | Override Possible? | Override Approver | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | Sanctions / PEP screen — MATCH | CRITICAL | NO | Compliance Officer | YES — immutable log | NO | N/A — must escalate | Match = immediate block. No agent action permitted. |
| 2 | UBO chain traversal — result delivered to client | HIGH | NO | Compliance Officer | YES | NO | N/A | Must be reviewed before sharing with client. |
| 3 | Conflict-of-interest — conflict found | HIGH | NO | Senior Partner / Legal | YES — immutable | YES (documented) | Managing Director + Legal | Documented waiver required. |
| 4 | Engagement letter — send to client | MEDIUM-HIGH | NO | Relationship Manager | YES | YES | Department Head | Agent drafts; human reviews and sends. |
| 5 | Banking introduction letter — send | MEDIUM-HIGH | NO | Relationship Manager | YES | YES | Department Head | Agent drafts; human reviews and sends. |
| 6 | Mandate renewal alert — internal notification | LOW | YES | None (automated) | YES (system log) | YES | Operations Manager | Alert only; no client-facing action. |
| 7 | Research output — share with client | MEDIUM | NO | Analyst / Relationship Manager | YES | YES | Senior Analyst | All research outputs reviewed for accuracy. |
| 8 | New entity added to GraphRAG schema | HIGH | NO | AI Lead + Data Lead | YES | NO | N/A — committee decision | Schema changes affect all agents. |
| 9 | New skill deployed to production | MEDIUM | NO | AI Lead (eval pass rate confirmed) | YES | NO | N/A | Requires EVAL.json pass rate ≥ 90% documented. |
| 10 | New agent deployed to production | HIGH | NO | AI Lead + Compliance Officer | YES | NO | N/A | Requires AGENT_SPEC.md complete + penetration test. |

---

## 3. Change Management Process

All changes to the AI system follow a structured lifecycle to prevent regressions.

### 3.1 Change Categories

| Category | Examples | Approval Required | Lead Time |
|---|---|---|---|
| **Schema Change** | New entity/relationship type in GraphRAG | AI Lead + Data Lead | 5 business days |
| **Agent Change** | New agent, system prompt update, tool permission change | AI Lead + Compliance Officer | 3 business days |
| **Skill Change** | New skill, logic update, eval threshold change | AI Lead (eval pass confirmed) | 2 business days |
| **Tool Change** | New MCP server, API credential rotation, permission change | Engineering Lead + AI Lead | 3 business days |
| **Policy Change** | Data retention, PII handling, approval matrix update | Legal + Compliance + AI Lead | 10 business days |

### 3.2 Change Request Workflow

1. **Requester** submits a Change Request (CR) with: scope, rationale, impacted layers, rollback plan.
2. **Reviewer** (per table above) evaluates the CR against architecture constraints.
3. **Eval Gate** — if the change touches L4 (Skills) or L5 (Agents), the EVAL.json suite must pass at ≥ 90% before merge.
4. **Deploy** — change is deployed to staging, validated, then promoted to production.
5. **Post-Deploy Audit** — audit log entry confirms: who approved, when deployed, eval pass rate, rollback plan.

### 3.3 Rollback Policy
- Every change must have a documented rollback plan before deployment.
- Rollback authority: the original Approver or any higher-level authority.
- Rollback must be executable within 1 hour of detection of a regression.

---

## 4. Incident Response

### 4.1 Incident Severity Levels

| Severity | Definition | Response Time | Escalation |
|---|---|---|---|
| **SEV-1 (Critical)** | Sanctions match acted upon without human approval; PII leak; compliance breach | Immediate (< 15 min) | Compliance Officer → Managing Director → Legal |
| **SEV-2 (High)** | Agent produces incorrect compliance output; tool unavailable for blocking check | < 1 hour | AI Lead → Compliance Officer |
| **SEV-3 (Medium)** | Research output inaccuracy; document draft contains errors caught in review | < 4 hours | AI Lead → Department Head |
| **SEV-4 (Low)** | Non-blocking alert failure; cosmetic output issue; latency degradation | < 24 hours | Engineering Lead |

### 4.2 Incident Response Steps

1. **Detect**: Triggered by audit log anomaly, human report, or automated monitoring.
2. **Contain**: Immediately disable the affected agent/skill/tool. Activate fallback.
3. **Investigate**: AI Lead + relevant specialist review logs, inputs, outputs.
4. **Remediate**: Fix root cause. Run EVAL.json regression suite.
5. **Post-Mortem**: Document: what happened, why, what was the impact, how to prevent recurrence.
6. **Policy Update**: If the incident reveals a governance gap, update this document.

### 4.3 Incident Log Schema
```json
{
  "incident_id": "string (UUID)",
  "severity": "SEV-1 | SEV-2 | SEV-3 | SEV-4",
  "detected_by": "string (human name or monitoring system)",
  "detection_timestamp": "ISO 8601",
  "affected_layer": "L1 | L2 | L3 | L4 | L5 | L6",
  "affected_component": "string (agent/skill/tool name)",
  "description": "string",
  "containment_action": "string",
  "resolution": "string",
  "root_cause": "string",
  "post_mortem_link": "string (URL to post-mortem doc)",
  "policy_update_required": "boolean",
  "resolved_timestamp": "ISO 8601"
}
```

---

## 5. Audit Trail Requirements

### 5.1 What Must Be Logged

| Event Type | Fields Logged | Retention Period | Immutable? |
|---|---|---|---|
| Agent routing decision | session_id, intent_label, routing_target, confidence_score, timestamp | 2 years | YES |
| Skill execution | session_id, skill_id, input_hash, output_hash, pass/fail, timestamp | 2 years | YES |
| Compliance check result | session_id, check_type, entity_id, result, evidence_ref, approver, timestamp | 7 years | YES |
| Tool API call | session_id, tool_name, agent_id, request_hash, response_status, timestamp | 1 year | NO |
| Human override | session_id, original_output, override_action, overrider_name, justification, timestamp | 7 years | YES |
| Schema / agent / skill change | change_id, component, change_type, approver, eval_pass_rate, deploy_timestamp | Indefinite | YES |

### 5.2 Log Integrity
- All immutable logs must use append-only storage with cryptographic hash chaining.
- No agent may modify or delete its own audit logs.
- Compliance-related logs (sanctions, UBO, conflict) must be accessible for regulatory audit within 24 hours of request.

---

## 6. AI Use Policy

### 6.1 Permitted Uses
- Answering jurisdiction and regulatory research questions with source citations.
- Drafting documents for human review (never auto-sent to clients).
- Running compliance checks with human approval gates on all blocking results.
- Internal operational alerts and report assembly.
- Client context lookup and session management.

### 6.2 Prohibited Uses
- **No autonomous client communication**: No agent may send email, chat, or documents to a client without human review and explicit approval.
- **No autonomous compliance decisions**: No agent may auto-clear a sanctions match, PEP hit, or conflict of interest.
- **No PII persistence in Working Memory**: All PII must be purged from Working Memory at session close.
- **No cross-client data leakage**: No agent may use Client A's data to inform a response about Client B, unless explicitly authorised by a conflict-check clearance.
- **No unsupervised learning**: Agents do not self-modify their system prompts or skill logic. All updates go through the Change Management Process.

### 6.3 Transparency Requirements
- Every agent output that reaches a client must disclose that it was AI-generated and human-reviewed.
- Confidence scores must be visible to the reviewing human — never hidden from the approval workflow.
- Source citations must accompany all research outputs.

---

## 7. Data Retention Policy

| Data Type | Retention Period | Deletion Trigger | Owner |
|---|---|---|---|
| Episodic Memory (active client) | Retain while client is active | Client off-boarding + 2 years | AI Lead / Compliance |
| Episodic Memory (archived client) | 2 years post final mandate end | Automatic purge at 2-year mark | Data / Compliance |
| Semantic Memory (SOPs, regulations) | Indefinite (version-controlled) | Superseded versions archived, never deleted | AI Lead |
| Procedural Memory (skill patterns) | Indefinite | Purge only on skill deprecation | AI Lead |
| Working Memory (session state) | Ephemeral — end of session or 24h inactivity | Automatic purge | System |
| Compliance audit logs | 7 years | Automatic archive at 7-year mark | Legal / Compliance |
| General audit logs | 2 years | Automatic archive | Engineering |
| Client PII (passports, DOBs) | Per data subject request or retention policy | Client request or regulatory mandate | Compliance / DPO |

---

## 8. Human Override Procedures

### 8.1 Override Authority Levels

| Override Scope | Who Can Override | Documentation Required |
|---|---|---|
| Agent routing decision | Relationship Manager or above | Log entry with justification |
| Skill output (non-compliance) | Department Head | Log entry with corrected output |
| Compliance check result (PASS→FAIL) | Compliance Officer | Immutable log + incident report |
| Compliance check result (FAIL→PASS) | Managing Director + Legal Counsel (dual sign-off) | Immutable log + documented waiver + rationale |
| System prompt change | AI Lead + Compliance Officer | Change request + eval regression pass |
| Emergency agent shutdown | Any Senior Manager | Post-incident report within 24 hours |

### 8.2 Override Workflow
1. Human identifies the need to override an agent output.
2. Human logs the override request with: original output, desired override, justification.
3. System verifies override authority level.
4. Override is applied and logged immutably.
5. If the override contradicts a compliance result, a mandatory incident review is triggered within 48 hours.

---

## 9. Review & Update Schedule

| Review Type | Frequency | Participants | Trigger |
|---|---|---|---|
| Full governance review | Bi-annual (every 6 months) | Legal, Compliance, AI Lead, Engineering Lead | Scheduled |
| Approval matrix review | Quarterly | AI Lead, Compliance Officer | Scheduled |
| Incident-driven review | Ad-hoc | All relevant stakeholders | Any SEV-1 or SEV-2 incident |
| Policy gap review | Ad-hoc | Legal, AI Lead | New regulation, new jurisdiction, or new agent deployment |

---

## 10. Document Cross-References

| Document | Layer | Relationship to GOVERNANCE.md |
|---|---|---|
| AGENT_SPEC_*.md | L5 | Each agent spec references this document for escalation rules and approval gates |
| SKILL_*.md | L4 | Each skill spec references this document for human-in-loop gate definitions |
| EVAL_*.json | L4 | Eval pass rates are a governance gate for deployment (Section 3) |
| TOOL_REGISTRY.md | L3 | Tool permissions and audit requirements align with Section 5 |
| MEMORY_SCHEMA.md | L2 | Retention policies in Section 7 must match memory schema definitions |
| GRAPH_SCHEMA.md | L1 | Schema changes require governance approval per Section 2 |
