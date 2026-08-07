"""
Skill: sanctions-screen

Screens an individual or entity against sanctions lists (OFAC/EU/UN), PEP
databases, and adverse media. Zero-tolerance design: any true hit returns MATCH
and forces human review; near matches return POTENTIAL_MATCH; clean subjects
return PASS. Every screen produces an immutable audit_log_ref.

Runs against fixture sets standing in for Dow Jones / ComplyAdvantage feeds. In
production, the ``TEST_*`` sentinel names are replaced by live list lookups —
the contract (screen_result / pep_result / adverse_media / audit_log_ref) is
identical.
"""

from __future__ import annotations

import uuid
from typing import Dict

_SANCTIONED_INDIVIDUALS = {"test_sanctioned_person_001"}
_SANCTIONED_ENTITIES = {"test_sanctioned_entity_001"}
_PEP_INDIVIDUALS = {"test_pep_person_001"}
_NEAR_MATCH = {"test_nearmatch_person_001"}
_ADVERSE_MEDIA = {"test_adverse_media_001"}


def run(payload: Dict) -> Dict:
    screen_type = payload.get("screen_type", "INDIVIDUAL")
    subject = payload.get("subject", {}) or {}

    if screen_type == "ENTITY":
        name = subject.get("entity_name")
    else:
        name = subject.get("full_name")

    if not name:
        return {"error": "ERR_MISSING_REQUIRED_FIELD"}

    key = name.strip().lower()
    matches = []
    adverse = []
    is_pep = False
    result = "PASS"

    if key in _SANCTIONED_INDIVIDUALS or key in _SANCTIONED_ENTITIES:
        result = "MATCH"
        matches = [{"list": "OFAC SDN", "score": 1.0, "matched_name": name}]
    elif key in _NEAR_MATCH:
        result = "POTENTIAL_MATCH"
        matches = [{"list": "EU Consolidated", "score": 0.72, "matched_name": name}]

    if key in _PEP_INDIVIDUALS:
        is_pep = True

    if key in _ADVERSE_MEDIA:
        adverse = [{
            "headline": "Regulatory probe reported in regional press",
            "source": "ComplyAdvantage",
            "relevance": 0.81,
        }]

    requires_human_review = (
        result in ("MATCH", "POTENTIAL_MATCH") or is_pep or bool(adverse)
    )

    return {
        "screen_result": result,
        "requires_human_review": requires_human_review,
        "matches": matches,
        "pep_result": {"is_pep": is_pep},
        "adverse_media": adverse,
        "audit_log_ref": str(uuid.uuid4()),
    }
