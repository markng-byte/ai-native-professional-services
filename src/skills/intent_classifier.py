"""
Skill: intent-classifier

Routes an inbound natural-language message to the correct specialist agent by
classifying it into one of the canonical intents:
RESEARCH, COMPLIANCE, DRAFTING, OPERATIONS, or AMBIGUOUS.

Rules that matter for correctness (encoded in the eval suite):
  * Compliance-first — when a message contains both a compliance signal
    (KYC / sanctions / UBO / conflict) and another intent, it routes to
    Compliance so nothing risky slips through drafting/ops.
  * Vague messages return AMBIGUOUS with low confidence and escalate to a
    human intake officer rather than guessing.
  * Classification tolerates minor spelling errors.
"""

from __future__ import annotations

from typing import Dict

_COMPLIANCE_KW = (
    "sanction", "screen", "pep", "kyc", "aml", "adverse media",
    "ubo", "beneficial owner", "conflict of interest", "conflict",
    "due diligence",
)
_RESEARCH_KW = (
    "compare", "versus", " vs ", "jurisdiction", "substance requirement",
    "substance requirements", "incorporat", "which is better", "regulation",
    "regulatory", "requirements for", "holding company",
)
_DRAFTING_KW = (
    "draft", "engagement letter", "banking introduction", "engagement",
    "letter", "agreement", "memo",
)
# Fuzzy fragments that survive common misspellings ("engagment leter", "draf").
_DRAFTING_FUZZY = ("engag", "leter", "letr", "draf")
_OPERATIONS_KW = (
    "renew", "expir", "deadline", "filing", "due", "calendar", "report",
    "portfolio summary", "mandates are expiring", "summary report",
)


def _classify(message: str):
    p = " " + (message or "").lower() + " "

    compliance = any(k in p for k in _COMPLIANCE_KW)
    research = any(k in p for k in _RESEARCH_KW)
    drafting_exact = any(k in p for k in _DRAFTING_KW)
    drafting_fuzzy = any(k in p for k in _DRAFTING_FUZZY)
    operations = any(k in p for k in _OPERATIONS_KW)

    if compliance:
        multi_intent = drafting_exact or drafting_fuzzy or research or operations
        confidence = 0.85 if multi_intent else 0.95
        return "COMPLIANCE", "Compliance Agent", confidence
    if research:
        return "RESEARCH", "Research Agent", 0.92
    if drafting_exact:
        return "DRAFTING", "Drafting Agent", 0.93
    if operations:
        return "OPERATIONS", "Operations Agent", 0.88
    if drafting_fuzzy:
        # Matched only via a fuzzy fragment — lower confidence, still routed.
        return "DRAFTING", "Drafting Agent", 0.78
    return "AMBIGUOUS", "Human Intake Officer", 0.42


def run(payload: Dict) -> Dict:
    message = payload.get("raw_message") or payload.get("user_request") or ""
    intent, routing, confidence = _classify(message)
    return {
        "intent_label": intent,
        "routing_target": routing,
        "next_agent_routing": routing,
        "confidence_score": confidence,
        "session_id": payload.get("session_id"),
    }
