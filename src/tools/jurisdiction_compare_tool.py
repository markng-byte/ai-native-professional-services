"""
CrewAI tool wrapper for the ``jurisdiction-compare`` skill.

This file previously held its own ``mock_data`` copy of the jurisdiction
fixture — a third copy alongside ``src/engine.py`` and the skill itself — so the
agent runtime could quote figures that differed from the gated skill.

It is now a thin adapter over the single gated implementation. Returns JSON
(the previous version returned a Python ``repr`` via ``str(dict)``, which is not
valid JSON and is awkward for an LLM to parse).
"""

from __future__ import annotations

import json
from typing import List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from skills import SKILLS


class JurisdictionCompareInput(BaseModel):
    """Input schema for JurisdictionCompareTool."""
    jurisdictions: List[str] = Field(
        ..., description="List of ISO 3166 jurisdiction codes (e.g., ['VG', 'KY'])."
    )


class JurisdictionCompareTool(BaseTool):
    name: str = "jurisdiction_compare"
    description: str = (
        "Compares two or more jurisdictions across cost, tax, timeline, substance, and "
        "compliance dimensions, using the firm's verified jurisdiction knowledge."
    )
    args_schema: Type[BaseModel] = JurisdictionCompareInput

    def _run(self, jurisdictions: List[str]) -> str:
        result = SKILLS["jurisdiction-compare"]({"jurisdictions": jurisdictions})
        return json.dumps(result)
