# Skill Specification: intent-classifier

## 1. Name
`intent-classifier`

## 2. Description
This skill analyzes incoming user messages or internal system triggers to accurately determine the user's underlying intent. It is an internal routing capability used exclusively by the Orchestrator agent to classify the nature of a request (e.g., research, document drafting, compliance check, or operational task) and map it to the correct downstream specialist agent. It should trigger on every initial inbound message that begins a new session or changes the topic mid-session.

## 3. Trigger Phrases
*This is an internal skill triggered automatically by the Orchestrator on new messages. Example user phrases it classifies include:*
- "Can you compare the tax implications of setting up in BVI versus Cayman?"
- "I need an engagement letter drafted for Client X's new mandate."
- "Who is the ultimate beneficial owner of ABC Holdings?"
- "Which of our client mandates are due for renewal next month?"
- "Please run a sanctions screen on John Doe."

## 4. Input Format
```json
{
  "session_id": "string (UUID)",
  "raw_message": "string (The unedited user input or system event)",
  "client_context": "object (Optional: Known client profile data from prior turns)"
}
```

## 5. Output Format
```json
{
  "intent_label": "string (Enum: RESEARCH, DRAFTING, COMPLIANCE, OPERATIONS, AMBIGUOUS)",
  "routing_target": "string (Agent Name or 'Human Intake Officer')",
  "confidence_score": "float (0.0 to 1.0)",
  "extracted_entities": {
    "client_names": ["string"],
    "jurisdictions": ["string"],
    "service_types": ["string"]
  }
}
```

## 6. Steps
1. **Receive Input**: Accept the `raw_message` and any existing `client_context`.
2. **Entity Extraction**: Scan the text for explicit mentions of entities (jurisdictions, document types, names, service types).
3. **Intent Classification**: Evaluate the message against the predefined intent categories:
   - *RESEARCH*: General queries about rules, comparisons, or eligibility.
   - *DRAFTING*: Requests to create, write, or format documents.
   - *COMPLIANCE*: Inquiries regarding UBOs, KYC/AML, conflicts of interest, or sanctions.
   - *OPERATIONS*: Requests involving internal records, deadlines, renewals, or reporting.
4. **Confidence Scoring**: Assign a confidence score based on the clarity of the request.
5. **Routing Assignment**: Map the `intent_label` to the corresponding specialist agent. If the `confidence_score` is below 0.8, set `intent_label` to AMBIGUOUS and `routing_target` to 'Human Intake Officer'.
6. **Return Output**: Format the results into the required JSON schema and return to the Orchestrator.

## 7. Dependencies
- None (Pure LLM classification task. No external tools, APIs, or MCP servers required).

## 8. Human-in-the-Loop Gates
- **No Direct Human Gate**: This skill executes automatically in the background. However, if it outputs an `AMBIGUOUS` intent (Confidence < 0.8), the Orchestrator's routing logic will escalate the session to a Human Intake Officer.

## 9. Eval Criteria
- **Eval File**: `EVAL_intent-classifier.json` (To be created)
- **Minimum Pass Rate**: 95% classification accuracy on a standard set of 50+ diverse prompt examples.
- **Success Definition**: The skill must correctly match the `raw_message` to the exact `intent_label` defined in the test case without false positives for high-risk compliance tasks.
- **Edge Cases to Test**: Multi-intent messages (e.g., "Draft a letter and run a KYC check"), highly vague requests ("Can you help with my company?"), and misspelled inputs.

## 10. Compatibility
- **Environment**: Compatible with standard LLM contexts.
- **Permissions**: Requires no read/write permissions to external systems or databases. Operates purely on the text payload provided in the input.

## 11. Version + Changelog
- **Version**: 1.0.0
- **Last Updated**: 2026-04-29
- **Change Summary**: Initial creation of the intent-classifier skill specification for the L4 Skill & Workflow Layer.
