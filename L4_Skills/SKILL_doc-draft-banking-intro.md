# Skill Specification: doc-draft-banking-intro

## 1. Name
`doc-draft-banking-intro`

## 2. Description
This skill generates a first-draft banking introduction letter to present a client to a target bank for account opening. It pulls entity data, ownership structure, and historical banking success rates from GraphRAG and CRM, selects the appropriate bank-specific template, and generates a personalized letter. Should trigger on "banking introduction letter," "bank referral letter," or "introduce client to bank" requests.

## 3. Trigger Phrases
- "Banking introduction letter"
- "Bank referral letter"
- "Introduce client to HSBC"
- "Need a bank intro for new BVI company"
- "Account opening letter"

## 4. Input Format
```json
{
  "session_id": "string (UUID)",
  "client_id": "string",
  "target_bank": "string (e.g., HSBC, DBS, BNP Paribas)",
  "account_type": "string (optional — CORPORATE, PERSONAL, ESCROW)",
  "additional_notes": "string (optional — special requirements)"
}
```

## 5. Output Format
```json
{
  "draft_content": "string (Markdown or base64-encoded DOCX)",
  "format": "string (MARKDOWN / DOCX)",
  "template_used": "string",
  "target_bank": "string",
  "bank_requirements_summary": "string (known requirements for this bank + jurisdiction combo)",
  "missing_fields": ["string"],
  "data_sources_used": ["string"],
  "historical_success_rate": "float (optional — past success rate for this bank + entity profile combo)",
  "requires_human_review": true,
  "reviewer_role": "Relationship Manager"
}
```

## 6. Steps
1. **Validate Input**: Confirm `client_id` exists and `target_bank` is recognised.
2. **Client Data Pull**: Query GraphRAG for full entity profile: `registered_name`, `jurisdiction`, directors, UBOs, existing bank accounts.
3. **Bank Requirements Lookup**: Query Semantic Memory for the target bank's known requirements (from Bank Account Opening Guidelines in corpus).
4. **Historical Success Check**: Query CRM for past banking intro mandates with the same `target_bank + jurisdiction` combo. Compute success rate if data exists.
5. **Template Selection**: Retrieve the banking intro template (generic or bank-specific) from Drive.
6. **Field Population**: Fill placeholders with client data and bank-specific fields.
7. **Generate Recommendation Note**: If `historical_success_rate < 0.3`, add a note suggesting the Relationship Manager consider alternative banks.
8. **Return to Drafting Agent**: Flag as `requires_human_review: true`.

## 7. Dependencies
- GraphRAG Query Engine (Read — entity + account data)
- Semantic Memory (Read — bank guidelines)
- Salesforce CRM (Read — mandate history for success rate)
- Google Drive / Docs MCP (Read — templates; Write — staging)

## 8. Human-in-the-Loop Gates
- **Always**: Every banking intro letter requires Relationship Manager review before sending to the bank. No exception.

## 9. Eval Criteria
- **Eval File**: `EVAL_doc-draft-banking-intro.json`
- **Minimum Pass Rate**: 90% field accuracy.
- **Edge Cases**: Bank not in guidelines corpus, client with no prior banking history, multi-currency account requests.

## 10. Compatibility
- Requires GraphRAG, Semantic Memory (bank guidelines), and Drive templates. Degrades if bank guidelines are missing — proceeds with generic template and flags output.

## 11. Version + Changelog
- **Version**: 1.0.0
- **Last Updated**: 2026-04-29
- **Change Summary**: Initial creation.
