# Skill Specification: sanctions-screen

## 1. Name
`sanctions-screen`

## 2. Description
This skill screens an individual or entity against international sanctions lists, PEP (Politically Exposed Person) databases, and adverse media sources. It is a critical compliance gate — no client onboarding can proceed without a completed sanctions screen. A MATCH result is an **immediate block** with no auto-resolution permitted. This skill should trigger on any onboarding request, any KYC refresh, and any explicit screening request. Even indirect phrasing like "is this person clean?" or "any issues with this individual?" should invoke this skill.

## 3. Trigger Phrases
- "Screen individual"
- "AML check"
- "PEP screening"
- "Run sanctions on John Doe"
- "Is this person on any watchlist?"
- "Any compliance issues with this individual?"
- "KYC screening for new client"

## 4. Input Format
```json
{
  "session_id": "string (UUID)",
  "screen_type": "string (Enum: INDIVIDUAL, ENTITY)",
  "subject": {
    "full_name": "string (required)",
    "date_of_birth": "string (ISO 8601 — required for INDIVIDUAL)",
    "nationality": "string (ISO 3166 — optional)",
    "passport_number": "string (optional)",
    "entity_name": "string (required for ENTITY)",
    "jurisdiction_of_incorp": "string (optional for ENTITY)"
  }
}
```

## 5. Output Format
```json
{
  "screen_result": "string (Enum: PASS, MATCH, POTENTIAL_MATCH, ERROR)",
  "matches": [
    {
      "list_name": "string (e.g., OFAC SDN, EU Sanctions, UN Consolidated)",
      "match_score": "float (0.0–1.0)",
      "matched_name": "string",
      "match_details": "string",
      "list_date": "string (ISO 8601)"
    }
  ],
  "pep_result": {
    "is_pep": "boolean",
    "pep_level": "string (Enum: NATIONAL, REGIONAL, LOCAL, FAMILY_MEMBER, CLOSE_ASSOCIATE)",
    "details": "string"
  },
  "adverse_media": [
    {
      "source": "string",
      "headline": "string",
      "date": "string",
      "relevance_score": "float"
    }
  ],
  "screening_timestamp": "string (ISO 8601)",
  "requires_human_review": "boolean (true if any MATCH or POTENTIAL_MATCH)",
  "auto_approved": false,
  "audit_log_ref": "string (UUID)"
}
```

## 6. Steps
1. **Validate Input**: Confirm all required fields are present. Reject if `full_name` is missing.
2. **Sanctions List Query**: Call the Sanctions List API (ComplyAdvantage / Dow Jones) with the subject's name, DOB, and nationality.
3. **PEP Database Query**: Call the PEP database API with the same identifiers.
4. **Adverse Media Scan**: Query the adverse media module for recent coverage (last 24 months).
5. **Score Matches**: Any match with `match_score >= 0.85` → `screen_result: MATCH`. Scores between 0.6–0.84 → `POTENTIAL_MATCH`. Below 0.6 → discard.
6. **Immediate Block on MATCH**: If `screen_result == MATCH`, set `requires_human_review: true`, log immutably, and halt all downstream processing.
7. **Log to Episodic Memory**: Write the full screening result to the client's Episodic Memory with timestamp and audit reference.
8. **Return to Compliance Agent**: Deliver the structured result.

## 7. Dependencies
- Sanctions List API (ComplyAdvantage / Dow Jones) — **BLOCKING**: if unavailable, no onboarding proceeds.
- PEP Database API — **BLOCKING**: same rule.
- Episodic Memory (Write — immutable log entry)

## 8. Human-in-the-Loop Gates
- **Any MATCH**: Immediate escalation to Compliance Officer. No agent may clear, dismiss, or override a match.
- **Any POTENTIAL_MATCH**: Escalation to Compliance Officer for manual review and determination.
- **PASS result**: No human gate required (auto-approved for the screening step, though the broader onboarding workflow still requires overall human approval).

## 9. Eval Criteria
- **Eval File**: `EVAL_sanctions-screen.json`
- **Minimum Pass Rate**: **100%** — zero tolerance for missed matches on known test cases.
- **Edge Cases**: Name transliterations (Arabic, Chinese names), common name false positives, expired sanctions entries, entities vs. individuals with same name.

## 10. Compatibility
- Requires live Sanctions List API and PEP Database API. No degraded mode — if APIs are down, screening is blocked entirely and human must screen manually.

## 11. Version + Changelog
- **Version**: 1.0.0
- **Last Updated**: 2026-04-29
- **Change Summary**: Initial creation.
