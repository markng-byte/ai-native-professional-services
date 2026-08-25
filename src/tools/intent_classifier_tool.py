"""
CrewAI tool wrapper for the ``intent-classifier`` skill.

This file previously carried its **own** keyword classifier, which meant intent
classification existed in three places (here, ``src/engine.py``, and
``src/skills/intent_classifier.py``) with only the skill under the eval gate.
The agent runtime could therefore return a different answer from the verified
implementation.

It is now a thin adapter: the gated skill is the single source of truth and this
class only translates the call convention (master prompt §12, §26).
"""

from __future__ import annotations

import json
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from skills import SKILLS


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
        result = SKILLS["intent-classifier"]({"raw_message": user_request})
        return json.dumps({
            "intent_label": result["intent_label"],
            "confidence_score": result["confidence_score"],
            "next_agent_routing": result["routing_target"],
        })
