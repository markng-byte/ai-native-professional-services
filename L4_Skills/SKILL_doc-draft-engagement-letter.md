# Skill Specification: doc-draft-engagement-letter

## 1. Name
`doc-draft-engagement-letter`

## 2. Description
This skill generates a first-draft engagement letter (Letter of Engagement / LOE) for a new or renewed service mandate. It pulls client data from GraphRAG, selects the appropriate template from Drive, fills all variable fields, and returns a complete draft for human review. Should trigger on any "draft engagement letter," "prepare LOE," or "onboarding letter" request.

## 3. Trigger Phrases
- "Draft engagement letter"
- "Prepare LOE"
- "Onboarding letter for new client"
- "Engagement letter for company formation"
- "Letter of engagement for accounting mandate"

## 4. Input Format
```json
{
  "session_id": "string (UUID)",
  "client_id": "string",
  "service_type": "string (e.g., COMPANY_FORMATION, ACCOUNTING, REGISTERED_AGENT, BANKING_INTRO)",
  "mandate_details": {
    "jurisdiction": "string (ISO 3166)",
    "fee": "number (optional)",
    "currency": "string (optional — default USD)",
    "start_date": "string (ISO 8601 — optional, defaults to today)"
  }
}
```

## 5. Output Format
```json
{
  "draft_content": "string (Markdown or base64-encoded DOCX)",
  "format": "string (MARKDOWN / DOCX)",
  "template_used": "string (template file reference)",
  "missing_fields": ["string (placeholders that could not be auto-filled)"],
  "data_sources_used": ["string"],
  "requires_human_review": true,
  "reviewer_role": "Relationship Manager"
}
```

## 6. Steps
1. **Validate Input**: Confirm `client_id` exists and `service_type` is valid.
2. **Client Data Pull**: Query GraphRAG for: `full_legal_name`, `registered_address`, `jurisdiction_of_incorp`, directors, and UBOs.
3. **Template Selection**: Retrieve the engagement letter template for the specified `service_type` from Google Drive.
4. **Field Population**: Replace all template placeholders with client data (`{{client_name}}`, `{{jurisdiction}}`, `{{fee}}`, `{{service_description}}`, etc.).
5. **Missing Field Detection**: If any placeholder cannot be filled, add it to `missing_fields` and leave the placeholder visible in the draft.
6. **Format Output**: Generate the draft in the requested format.
7. **Return to Drafting Agent**: Flag as `requires_human_review: true`.

## 7. Dependencies
- GraphRAG Query Engine (Read — client entity data)
- Google Drive / Docs MCP (Read — templates; Write — save draft to staging)
- Salesforce CRM (Read — mandate and fee details)

## 8. Human-in-the-Loop Gates
- **Always**: Every engagement letter draft requires Relationship Manager review before sending to client. No exception.

## 9. Eval Criteria
- **Eval File**: `EVAL_doc-draft-engagement-letter.json`
- **Minimum Pass Rate**: 90% field accuracy (correct data in correct placeholder).
- **Edge Cases**: Client with multiple legal entities (which one?), missing fee schedule, new service type with no template.

## 10. Compatibility
- Requires Google Drive templates and live GraphRAG. If Drive is unavailable, use cached template and flag output.

## 11. Version + Changelog
- **Version**: 1.0.0
- **Last Updated**: 2026-04-29
- **Change Summary**: Initial creation.
