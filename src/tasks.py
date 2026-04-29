from crewai import Task

class ProfessionalServicesTasks:
    def executive_synthesis_task(self, agent, user_request):
        """
        Task for the Executive Assistant to process the final output for the executive.
        """
        return Task(
            description=(
                f"Process the executive's request: '{user_request}'.\n"
                f"You must delegate to the appropriate specialist agents (like Research or Compliance) "
                f"to gather the necessary data. Once you receive their outputs, synthesize them into "
                f"a high-level, structured Executive Brief. Use tables, bullet points, and clear action items."
            ),
            expected_output=(
                "A clean, professional Executive Brief in Markdown format. It MUST include "
                "a status indicator (✅ Done, ⏳ In progress, or ❓ Need input), a summary, "
                "and structured data from the sub-agents."
            ),
            agent=agent
        )

    def intake_classification_task(self, agent, user_request):
        """
        L4 Skill: intent-classifier
        Task for the Orchestrator to classify the incoming request.
        """
        return Task(
            description=(
                f"Analyze the following user request and classify its intent.\n"
                f"User Request: '{user_request}'\n\n"
                f"You must determine if this is a RESEARCH, COMPLIANCE, DRAFTING, or OPERATIONS request. "
                f"If you need more information to proceed (e.g., missing client name), state what is missing."
            ),
            expected_output=(
                "A JSON object matching the intent-classifier output contract, containing: "
                "intent_label, confidence_score, required_entities, and next_agent_routing."
            ),
            agent=agent
        )

    def jurisdiction_comparison_task(self, agent, jurisdictions):
        """
        L4 Skill: jurisdiction-compare
        Task for the Research Agent to compare multiple jurisdictions.
        """
        return Task(
            description=(
                f"Compare the following jurisdictions: {jurisdictions}.\n"
                f"Analyze them across 7 dimensions: cost, timeline, tax, substance, FATF status, "
                f"banking access, and compliance burden. "
                f"Use the firm's knowledge graph to gather the data."
            ),
            expected_output=(
                "A structured comparison table with one row per dimension, along with a recommendation "
                "and explicit source citations for every data point."
            ),
            agent=agent
        )

    def compliance_screening_task(self, agent, entity_details):
        """
        L4 Skill: sanctions-screen
        Task for the Compliance Agent to screen an entity.
        """
        return Task(
            description=(
                f"Perform a full sanctions, PEP, and adverse media screen on the following entity:\n"
                f"{entity_details}\n\n"
                f"You must query the external screening APIs and the internal conflict graph. "
                f"Any MATCH result is an immediate block."
            ),
            expected_output=(
                "A structured screening report with PASS/MATCH/POTENTIAL_MATCH status, "
                "a list of matches with scores, PEP result, and a required_human_review flag."
            ),
            agent=agent
        )
