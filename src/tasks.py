from crewai import Task

class ProfessionalServicesTasks:
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
