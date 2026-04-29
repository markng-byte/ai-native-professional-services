from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

class IntentClassifierInput(BaseModel):
    """Input schema for IntentClassifierTool."""
    user_request: str = Field(..., description="The raw natural language request from the user.")

class IntentClassifierTool(BaseTool):
    name: str = "intent_classifier"
    description: str = (
        "Classifies a user's request into one of the canonical intents: "
        "RESEARCH, COMPLIANCE, DRAFTING, OPERATIONS, or AMBIGUOUS."
    )
    args_schema: Type[BaseModel] = IntentClassifierInput

    def _run(self, user_request: str) -> str:
        # In a real implementation, this would either be an LLM call with structured output
        # or a fast text classifier (like a fine-tuned small model).
        
        lower_request = user_request.lower()
        
        if "compare" in lower_request or "jurisdiction" in lower_request:
            intent = "RESEARCH"
            routing = "Research Agent"
        elif "screen" in lower_request or "onboard" in lower_request or "conflict" in lower_request:
            intent = "COMPLIANCE"
            routing = "Compliance Agent"
        elif "draft" in lower_request or "letter" in lower_request:
            intent = "DRAFTING"
            routing = "Drafting Agent"
        else:
            intent = "AMBIGUOUS"
            routing = "Human Intake Officer"

        return f'{{"intent_label": "{intent}", "confidence_score": 0.95, "next_agent_routing": "{routing}"}}'
