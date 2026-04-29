# Skill Specification: ubo-chain-traverse

## 1. Name
`ubo-chain-traverse`

## 2. Description
This skill traverses the ownership graph to identify the Ultimate Beneficial Owner(s) of a given legal entity. It follows `OWNS` relationships through multiple hops (up to 5 levels) to find all individuals holding ≥25% beneficial ownership, either directly or through intermediate entities. This is a critical compliance capability — UBO identification is legally required in most jurisdictions before onboarding. The skill should trigger on any mention of "beneficial owner," "who owns," "UBO check," or "ownership structure."

## 3. Trigger Phrases
- "Find UBO of"
- "Who ultimately owns"
- "Beneficial owner check"
- "Ownership chain for"
- "Who is behind this company?"
- "Trace the ownership structure"

## 4. Input Format
```json
{
  "session_id": "string (UUID)",
  "entity_id": "string (Legal_Entity ID or Client ID)",
  "threshold_pct": "float (default: 25.0 — minimum ownership % to qualify as UBO)",
  "max_hops": "integer (default: 5 — maximum traversal depth)"
}
```

## 5. Output Format
```json
{
  "entity_id": "string",
  "entity_name": "string",
  "ubo_list": [
    {
      "individual_id": "string",
      "full_name": "string",
      "nationality": "string",
      "beneficial_pct": "float",
      "ownership_path": ["string (entity chain from UBO to target)"],
      "path_length": "integer",
      "pep_flag": "boolean",
      "sanction_flag": "boolean"
    }
  ],
  "total_ubos_found": "integer",
  "unresolved_chains": ["string (entity IDs where ownership could not be resolved)"],
  "chain_exceeded_max_hops": "boolean",
  "requires_human_review": "boolean",
  "audit_log_ref": "string (UUID)"
}
```

## 6. Steps
1. **Validate Input**: Confirm `entity_id` exists in GraphRAG. If not, return `ERR_ENTITY_NOT_IN_GRAPH`.
2. **Initial Traversal**: Execute Cypher query: `MATCH (i:Individual)-[:OWNS*1..{max_hops}]->(e:Legal_Entity {id: entity_id}) RETURN i, relationships`.
3. **Compute Beneficial %**: For each path, multiply intermediate ownership percentages to derive the effective beneficial ownership at the target entity.
4. **Apply Threshold**: Filter to individuals where `beneficial_pct >= threshold_pct`.
5. **Check Flags**: For each UBO found, pull `PEP_flag` and `sanction_flag` from the Individual node.
6. **Detect Unresolved Chains**: If any intermediate entity has no inbound `OWNS` relationship (ownership unknown), log it as `unresolved_chain`.
7. **Depth Check**: If any path reaches `max_hops` without resolving to an Individual, set `chain_exceeded_max_hops: true` and flag for human review.
8. **Log Immutably**: Write the full result to Episodic Memory.
9. **Return to Compliance Agent**.

## 7. Dependencies
- GraphRAG Query Engine (Read — deep multi-hop traversal)
- Episodic Memory (Write — immutable audit log)

## 8. Human-in-the-Loop Gates
- **Chain > 3 hops**: Flag for Compliance Officer review (complex structure).
- **Chain exceeds max_hops**: Mandatory human review — ownership could not be fully resolved.
- **Unresolved chains**: Mandatory human review — missing ownership data.
- **Any UBO with PEP or sanction flag**: Immediate escalation to Compliance Officer.

## 9. Eval Criteria
- **Eval File**: `EVAL_ubo-chain-traverse.json`
- **Minimum Pass Rate**: 95% accuracy on known ownership structures with pre-calculated UBO answers.
- **Edge Cases**: Circular ownership, 100% single-owner chains, nominee structures, trusts, foundations without clear ownership.

## 10. Compatibility
- Requires live GraphRAG with fully populated `OWNS` relationships. No degraded mode — cannot compute UBO without graph data.

## 11. Version + Changelog
- **Version**: 1.0.0
- **Last Updated**: 2026-04-29
- **Change Summary**: Initial creation.
