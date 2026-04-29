# Skill Specification: doc-expiry-scan

## 1. Name
`doc-expiry-scan`

## 2. Description
This skill scans the knowledge graph for documents (passports, certificates of incorporation, bank letters, UBO declarations) that are expiring within a specified date threshold. It produces an actionable list of entities whose documents need renewal, enabling proactive KYC refresh and compliance maintenance. Should trigger on any "expiring documents," "KYC refresh needed," or "expired passport" query.

## 3. Trigger Phrases
- "Expiring documents"
- "KYC refresh needed"
- "Expired passport"
- "Documents due for renewal"
- "Which clients have stale documentation?"

## 4. Input Format
```json
{
  "session_id": "string (UUID)",
  "date_threshold_days": "integer (default: 30 — scan for docs expiring within N days)",
  "doc_types": ["string (optional — filter by: PASSPORT, CERT_OF_INCORP, UBO_DECLARATION, BANK_LETTER)"],
  "jurisdiction_filter": "string (optional — ISO 3166)"
}
```

## 5. Output Format
```json
{
  "expiring_documents": [
    {
      "doc_id": "string",
      "doc_type": "string",
      "expiry_date": "string (ISO 8601)",
      "days_until_expiry": "integer",
      "related_entity_id": "string",
      "related_entity_name": "string",
      "entity_type": "string (Individual / Legal_Entity)",
      "assigned_officer": "string",
      "jurisdiction": "string"
    }
  ],
  "total_expiring": "integer",
  "already_expired": "integer",
  "scan_timestamp": "string (ISO 8601)"
}
```

## 6. Steps
1. **Validate Input**: Set defaults for `date_threshold_days` (30) if not provided.
2. **GraphRAG Query**: `MATCH (e)-[:RELATED_DOCUMENT]->(d:Document) WHERE d.expiry_date <= date() + duration({days: threshold}) RETURN e, d`.
3. **Filter**: Apply optional `doc_types` and `jurisdiction_filter`.
4. **Enrich**: For each result, pull the assigned officer from the linked `Service_Mandate` or `Client` node.
5. **Sort**: Order by `days_until_expiry` ascending (most urgent first). Separate already-expired docs (negative days).
6. **Return to Compliance Agent / Operations Agent**.

## 7. Dependencies
- GraphRAG Query Engine (Read)

## 8. Human-in-the-Loop Gates
- **No direct human gate**: This is an alert/reporting skill. However, the output feeds into the Operations Agent's alert workflow, which may trigger client contact (requiring human action).

## 9. Eval Criteria
- **Eval File**: `EVAL_doc-expiry-scan.json`
- **Minimum Pass Rate**: 98% — must not miss any expiring document in test dataset.
- **Edge Cases**: Documents with no expiry date, documents linked to archived/inactive clients, multiple documents for same entity.

## 10. Compatibility
- Requires GraphRAG with `Document` nodes that have `expiry_date` populated.

## 11. Version + Changelog
- **Version**: 1.0.0
- **Last Updated**: 2026-04-29
- **Change Summary**: Initial creation.
