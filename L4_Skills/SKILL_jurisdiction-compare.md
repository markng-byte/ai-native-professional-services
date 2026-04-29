# Skill Specification: jurisdiction-compare

## 1. Name
`jurisdiction-compare`

## 2. Description
This skill compares two or more jurisdictions across key dimensions relevant to corporate service clients: incorporation costs, timelines, tax treatment, substance requirements, FATF status, banking access, and compliance burden. It is the most frequently used Research Agent skill and should trigger whenever a user asks about choosing between jurisdictions, cost comparisons, or regulatory differences. Even partial mentions like "which is better, BVI or Cayman?" should invoke this skill.

## 3. Trigger Phrases
- "Compare BVI vs Cayman"
- "Which jurisdiction for a fund?"
- "Cost comparison between Singapore and Hong Kong"
- "What are the differences between BVI and Cayman for a holding company?"
- "Substance requirements — BVI vs Cayman vs UAE"
- "Which jurisdiction is cheapest for incorporation?"

## 4. Input Format
```json
{
  "session_id": "string (UUID)",
  "jurisdictions": ["string (ISO 3166 codes — minimum 2, maximum 4)"],
  "client_profile": {
    "entity_type": "string (optional: LLC, Ltd, Foundation, Fund)",
    "industry": "string (optional)",
    "residency_of_ubo": "string (optional — ISO 3166)"
  },
  "comparison_dimensions": ["string (optional — subset of: cost, timeline, tax, substance, FATF, banking, compliance)"]
}
```

## 5. Output Format
```json
{
  "comparison_table": [
    {
      "dimension": "string",
      "jurisdiction_values": {
        "BVI": "string",
        "KY": "string"
      }
    }
  ],
  "recommendation": "string (optional — only if client_profile is provided)",
  "source_citations": ["string (document/URL references)"],
  "confidence_level": "string (HIGH / MEDIUM / LOW)",
  "data_freshness": {
    "jurisdiction_code": "string (last_updated ISO 8601)"
  }
}
```

## 6. Steps
1. **Validate Input**: Confirm ≥2 jurisdiction codes are valid ISO 3166. Default comparison dimensions to all 7 if not specified.
2. **GraphRAG Query**: For each jurisdiction, query `Jurisdiction` entity and its connected `Regulator`, `Service_Type`, and `Document` nodes.
3. **Semantic Memory Lookup**: Pull SOPs and fee schedules from Semantic Memory for each jurisdiction.
4. **Web Search (if needed)**: If GraphRAG or Semantic Memory is missing data for a dimension, perform a targeted web search. Flag any web-sourced data as `source: web` with date.
5. **Build Comparison Table**: Assemble a structured table with one row per dimension.
6. **Generate Recommendation**: If `client_profile` is provided, score each jurisdiction against the profile and rank. If not, omit recommendation.
7. **Cite Sources**: Attach source citations for every data point.
8. **Return Output**: Deliver structured JSON to the Research Agent / Orchestrator.

## 7. Dependencies
- GraphRAG Query Engine (Read)
- Semantic Memory (Read — SOPs, fee schedules)
- Web Search API (Read — fallback only)

## 8. Human-in-the-Loop Gates
- No direct human gate. However, the Research Agent's escalation rules apply: if `confidence_level == LOW` or sources conflict, the output is flagged for human analyst review before sharing with client.

## 9. Eval Criteria
- **Eval File**: `EVAL_jurisdiction-compare.json`
- **Minimum Pass Rate**: 90% accuracy on comparison table values vs. known correct data.
- **Edge Cases**: Jurisdictions not in corpus, single-jurisdiction input (should reject), outdated fee schedules, conflicting web vs. graph data.

## 10. Compatibility
- Requires live GraphRAG and Semantic Memory. Degrades gracefully to web-only with LOW confidence flag.

## 11. Version + Changelog
- **Version**: 1.0.0
- **Last Updated**: 2026-04-29
- **Change Summary**: Initial creation.
