# Skill Specification: conflict-check

## 1. Name
`conflict-check`

## 2. Description
This skill checks whether a prospective new client or individual has any existing relationships (directorship, ownership, UBO status) with current clients that would constitute a conflict of interest. It traverses `IS_DIRECTOR_OF`, `OWNS`, `IS_UBO_OF`, and `CONFLICTS_WITH` relationships in the graph to detect overlaps. This skill must trigger on every onboarding request and whenever a "conflict of interest" or "related party" inquiry is made.

## 3. Trigger Phrases
- "Conflict of interest"
- "Can we onboard this client?"
- "Related party check"
- "Any overlap with existing clients?"
- "Check for conflicts before onboarding"

## 4. Input Format
```json
{
  "session_id": "string (UUID)",
  "new_client_profile": {
    "entity_name": "string",
    "jurisdiction": "string (ISO 3166)",
    "directors": [{"full_name": "string", "individual_id": "string (optional)"}],
    "ubos": [{"full_name": "string", "individual_id": "string (optional)"}]
  }
}
```

## 5. Output Format
```json
{
  "conflict_found": "boolean",
  "conflicts": [
    {
      "conflict_type": "string (Enum: DIRECTORSHIP_OVERLAP, OWNERSHIP_OVERLAP, UBO_OVERLAP, PRIOR_CONFLICT_FLAG)",
      "individual_name": "string",
      "existing_client_id": "string",
      "existing_client_name": "string",
      "relationship_details": "string",
      "severity": "string (Enum: LOW, MEDIUM, HIGH, CRITICAL)"
    }
  ],
  "total_conflicts": "integer",
  "recommendation": "string (Enum: PROCEED, PROCEED_WITH_WAIVER, BLOCK)",
  "requires_human_review": true,
  "audit_log_ref": "string (UUID)"
}
```

## 6. Steps
1. **Validate Input**: Confirm at least one director or UBO name/ID is provided.
2. **Name Resolution**: For each director/UBO, attempt to match against existing `Individual` nodes in GraphRAG (exact ID match first, then fuzzy name match at ≥0.85 threshold).
3. **Graph Traversal**: For each matched Individual, query all outbound `IS_DIRECTOR_OF`, `OWNS`, `IS_UBO_OF` relationships to find connected `Legal_Entity` and `Client` nodes.
4. **Check Existing Conflicts**: Query `CONFLICTS_WITH` edges for any pre-existing conflict flags.
5. **Classify Conflicts**: For each detected overlap, assign severity based on type and number of overlapping relationships.
6. **Generate Recommendation**: BLOCK if any CRITICAL severity. PROCEED_WITH_WAIVER if MEDIUM/HIGH (requires documented waiver). PROCEED if no conflicts.
7. **Log Immutably**: Write to Episodic Memory.
8. **Return to Compliance Agent**.

## 7. Dependencies
- GraphRAG Query Engine (Read — multi-path traversal)
- Episodic Memory (Write — immutable log)

## 8. Human-in-the-Loop Gates
- **Always**: Every conflict-check result requires human review. Even a PROCEED recommendation must be confirmed by the Compliance Officer before onboarding continues.
- **BLOCK recommendation**: Requires Senior Partner / Legal sign-off before any waiver.

## 9. Eval Criteria
- **Eval File**: `EVAL_conflict-check.json`
- **Minimum Pass Rate**: 95% on detection of known conflicts in test graph data.
- **Edge Cases**: Individuals with common names appearing across multiple clients, nominees acting for multiple structures, resolved vs. unresolved prior conflicts.

## 10. Compatibility
- Requires live GraphRAG. No degraded mode — conflict check cannot be approximated.

## 11. Version + Changelog
- **Version**: 1.0.0
- **Last Updated**: 2026-04-29
- **Change Summary**: Initial creation.
