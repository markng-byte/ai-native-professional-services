# UX Specification: Internal Chat Channel

**Version**: 1.0.0
**Status**: DRAFT
**Layer**: L6 — Interaction Surface
**Created**: 2026-04-29
**Owner**: Product / Design
**Roadmap Ref**: Deliverable #17 — Phase 4 (Weeks 11–12)

---

## 1. Channel Identity
- **Channel Name**: Internal AI Assistant (Chat)
- **Channel Type**: Text-based conversational interface
- **Users**: Internal staff — Relationship Managers, Compliance Officers, Operations Officers, Analysts
- **Access**: Authenticated via SSO (company credentials)
- **Platform**: Web-based (embedded in internal portal) + Slack/Teams integration (Phase 2)

---

## 2. Channel Description

The Internal Chat Channel is the primary interaction surface between firm staff and the AI-Native agent system. Staff send natural language requests and receive structured responses routed through the Orchestrator. This is **not** a client-facing channel — all client communication is handled by humans after reviewing agent outputs.

---

## 3. Input / Output Contract

### 3.1 Input (User → System)

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | YES | Free-text natural language input |
| `user_id` | string | YES (auto from SSO) | Authenticated user identity |
| `user_role` | string | YES (auto from SSO) | Role: RM, Compliance, Ops, Analyst, AI Lead |
| `attachments` | file[] | NO | PDF/DOCX uploads for document-related requests |
| `session_id` | string | AUTO | Persistent session ID for multi-turn conversations |

### 3.2 Output (System → User)

| Field | Type | Description |
|---|---|---|
| `response_text` | string (Markdown) | The main answer — formatted for readability |
| `agent_trace` | string[] | Which agents/skills were involved (transparency) |
| `confidence_indicator` | string (HIGH/MEDIUM/LOW) | Visual confidence badge |
| `source_citations` | object[] | Clickable references to source documents |
| `action_buttons` | object[] | Contextual actions (e.g., "Approve Draft", "Escalate", "View Full Report") |
| `human_gate_alert` | object | If a human gate was triggered, shows what needs approval |
| `error_message` | string | User-friendly error explanation if something failed |

---

## 4. Conversation Flows

### 4.1 Happy Path — Research Query
```
User:  "Compare BVI vs Cayman for a holding company"
System: [Orchestrator → intent-classifier → Research Agent → jurisdiction-compare]
        Returns: Comparison table + recommendation + sources
        Confidence: HIGH
        Action button: "Share with client" (triggers human review gate)
```

### 4.2 Happy Path — Onboarding Request
```
User:  "I need to onboard a new client — Sunrise Capital, BVI company, director is John Lee"
System: [Orchestrator → client-lookup (NOT_FOUND) → Prompts for details]
        "I don't have Sunrise Capital in the system. Please confirm:
         1. Full legal name
         2. Jurisdiction of incorporation
         3. Director names and DOBs for compliance screening"
User:  Provides details
System: [Compliance Agent → conflict-check → sanctions-screen → ubo-chain-traverse]
        Returns: All checks PASS
        Action button: "Generate Engagement Letter"
```

### 4.3 Escalation Path — Sanctions Match
```
User:  "Screen this individual: [name, DOB]"
System: [Compliance Agent → sanctions-screen → MATCH]
        ⚠️ ALERT: "Sanctions match detected. This request has been escalated to the
        Compliance Officer for review. No further action can be taken until resolved."
        Human gate alert: Compliance Officer notified via email + chat ping
```

---

## 5. Fallback Behavior

| Failure Scenario | User-Facing Behavior | Behind the Scenes |
|---|---|---|
| Intent cannot be classified (AMBIGUOUS) | "I'm not sure I understand your request. Could you rephrase, or would you like me to connect you with a colleague?" | Orchestrator logs; Human Intake Officer alerted |
| Agent fails mid-task | "I encountered an issue processing your request. A team member has been notified and will follow up. Reference: [job_id]" | Error logged; AI Lead alerted |
| Tool/API unavailable | "Some data sources are temporarily unavailable. I can provide a partial answer — would you like to proceed, or wait for full data?" | Degraded mode activated; stale warnings shown |
| Session timeout (24h inactivity) | "Your previous session has expired. Starting a new session — I don't have context from our last conversation." | Working Memory purged per GOVERNANCE.md |

---

## 6. Escalation Triggers (from Chat)

| User Action / Signal | System Response |
|---|---|
| User types "talk to a human" or "escalate" | Session transferred to Relationship Manager with full chat log |
| User types "this is wrong" or "incorrect" | Agent output flagged; AI Lead notified for eval review |
| 3+ failed classification attempts | Auto-escalate to Human Intake Officer |
| Compliance-critical keyword detected (e.g., "sanctions," "fraud") | Auto-route to Compliance Agent regardless of classification |

---

## 7. UI Components

| Component | Description | Behaviour |
|---|---|---|
| **Chat Input** | Text field + file attachment button | Supports multi-line input; Enter to send |
| **Response Card** | Structured response with collapsible sections | Markdown rendered; tables, code blocks supported |
| **Confidence Badge** | Color-coded indicator (🟢 HIGH, 🟡 MEDIUM, 🔴 LOW) | Visible on every response |
| **Agent Trace** | Expandable "How this was answered" section | Shows agent chain for transparency |
| **Action Buttons** | Context-specific CTA buttons | "Approve", "Reject", "Request Revisions", "Share" |
| **Human Gate Banner** | Orange banner when approval is needed | Shows reviewer name, decision status, SLA countdown |
| **Source Panel** | Sidebar with source documents | Clickable links to original documents |

---

## 8. Permissions by Role

| Role | Can Ask | Can Approve Drafts | Can Override Agent | Can View Compliance Results |
|---|---|---|---|---|
| Relationship Manager | All queries | YES | YES (with log) | YES (own clients) |
| Compliance Officer | All queries | NO | YES (compliance scope) | YES (all) |
| Operations Officer | Ops queries | NO | NO | NO |
| Analyst | Research queries | NO | NO | NO |
| AI Lead | All queries | YES | YES (all) | YES (all) |

---

## 9. Error Messages (User-Friendly)

| Error Code | User Message |
|---|---|
| `ERR_ROUTING_FAILED` | "I couldn't determine how to handle your request. Please try rephrasing." |
| `ERR_CLIENT_NOT_FOUND` | "I couldn't find that client in our system. Could you provide the full legal name or client ID?" |
| `ERR_GRAPH_UNAVAILABLE` | "Our knowledge base is temporarily offline. I can try a basic search — results may be incomplete." |
| `ERR_API_UNAVAILABLE` | "An external service is currently down. I'll retry automatically — please check back in a few minutes." |
| `ERR_SANCTIONS_BLOCK` | "This request has been blocked pending a compliance review. Reference: [job_id]." |

---

## 10. Cross-References

| Document | Relationship |
|---|---|
| `AGENT_SPEC_Orchestrator.md` | All chat input routes through the Orchestrator |
| `GOVERNANCE.md` | Defines approval gates shown as Human Gate Banners |
| `MEMORY_SCHEMA.md` | Working Memory rules govern session persistence |
