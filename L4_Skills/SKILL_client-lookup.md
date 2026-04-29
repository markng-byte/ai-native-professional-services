# Skill Specification: client-lookup

## 1. Name
`client-lookup`

## 2. Description
This skill retrieves a client's full profile, active mandates, and recent episodic history from the CRM and GraphRAG, establishing the contextual foundation for any session. It is triggered automatically by the Orchestrator whenever a client name, entity name, or client ID is detected in an inbound request. It should also trigger on any request where a client context is implied but not yet resolved. Without a successful client-lookup, most downstream skills cannot operate correctly — it is the prerequisite data hydration step for the entire session.

## 3. Trigger Phrases
*Internal skill triggered by the Orchestrator. Example signals that trigger it:*
- Any message containing a recognised client or entity name (e.g., "Acme Holdings," "Sunrise Capital")
- Any message containing a client ID reference
- Any message referencing "our client" or "the client"
- Start of any new session where a client-scoped task is implied
- Any request from the Drafting or Operations Agent that requires client data

## 4. Input Format
```json
{
  "session_id": "string (UUID)",
  "lookup_query": "string (Client name, trade name, or entity name as provided in raw_message)",
  "client_id": "string (Optional: If already known)",
  "lookup_mode": "string (Enum: FUZZY_NAME, EXACT_ID, ENTITY_NUMBER)"
}
```

## 5. Output Format
```json
{
  "client_id": "string",
  "full_legal_name": "string",
  "trade_name": "string (Optional)",
  "jurisdiction_of_incorp": "string (ISO 3166 code)",
  "risk_rating": "string (Enum: LOW, MEDIUM, HIGH, CRITICAL)",
  "active_mandates": [
    {
      "mandate_id": "string",
      "service_type": "string",
      "status": "string",
      "renewal_date": "string (ISO 8601 date)"
    }
  ],
  "assigned_officer": "string",
  "last_interaction_summary": "string (From Episodic Memory — last session summary)",
  "open_compliance_flags": ["string"],
  "lookup_confidence": "float (0.0 to 1.0)",
  "match_type": "string (Enum: EXACT, FUZZY, MULTIPLE_CANDIDATES, NOT_FOUND)"
}
```

## 6. Steps
1. **Receive Input**: Accept the `lookup_query` and `lookup_mode` from the Orchestrator.
2. **CRM Query**: Search the Salesforce CRM using the provided query. If `lookup_mode` is `EXACT_ID`, search by `client_id`. If `FUZZY_NAME`, apply fuzzy matching with a minimum similarity threshold of 0.8.
3. **Multiple Candidates Handling**: If fuzzy search returns >1 result, return all candidates with their similarity scores and set `match_type: MULTIPLE_CANDIDATES`. Pause and request Orchestrator to resolve ambiguity with the user.
4. **GraphRAG Enrichment**: On a successful CRM match, query the GraphRAG engine to pull the client's entity structure (associated Legal Entities, Officers, current UBO data).
5. **Episodic Memory Pull**: Retrieve the last session summary from Episodic Memory for this `client_id`.
6. **Compliance Flag Check**: Check if any open compliance flags (e.g., pending KYC, expired documents) are attached to the client record in the CRM.
7. **Assemble Output**: Combine all retrieved data into the defined output schema.
8. **Return to Orchestrator**: Deliver the enriched client profile to the Orchestrator for context injection into the active session's Working Memory.

## 7. Dependencies
- **Salesforce CRM** (MCP Server — Read access)
- **GraphRAG Query Engine** (Internal — Read access)
- **Episodic Memory** (Internal — Read access)

## 8. Human-in-the-Loop Gates
- **Multiple Candidates**: If `match_type == MULTIPLE_CANDIDATES`, the Orchestrator must surface the candidate list to the human user and request them to confirm the correct client before proceeding.
- **Not Found**: If `match_type == NOT_FOUND`, the Orchestrator must ask the user to provide more details. The session must not proceed on an unidentified client.

## 9. Eval Criteria
- **Eval File**: `EVAL_client-lookup.json`
- **Minimum Pass Rate**: 98% exact match on known client IDs; 90% fuzzy match accuracy on name variants.
- **Success Definition**: Retrieved `client_id` must match the ground-truth client for all test cases. Active mandates must be complete and not stale.
- **Edge Cases to Test**: Partial name matches, trade name vs legal name queries, retired clients, clients with multiple legal entities, clients with open compliance flags.

## 10. Compatibility
- **Environment**: Requires live CRM connection (Salesforce MCP), GraphRAG engine, and Episodic Memory store.
- **Permissions Required**: CRM Read, GraphRAG Read, Episodic Memory Read.
- **Degraded Mode**: If GraphRAG is unavailable, return CRM data only — flag output as `PARTIAL` and note missing entity graph data.

## 11. Version + Changelog
- **Version**: 1.0.0
- **Last Updated**: 2026-04-29
- **Change Summary**: Initial creation of the client-lookup skill specification for the L4 Skill & Workflow Layer.
