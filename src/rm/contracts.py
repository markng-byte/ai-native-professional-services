"""Result contracts for the Tier 2 RM workflows.

Registered into the shared contract registry so that one
``contracts.validate_envelope`` covers Tier 1 capabilities *and* Tier 2
workflows — and will cover Layer 4 runtime validation unchanged.
"""

from __future__ import annotations

from typing import Dict

WORKFLOW_CONTRACTS: Dict[str, Dict[str, str]] = {
    "rm-client-summary": {
        "client_id": "str",
        "client_summary": "str",
        "opportunity_summary": "list",
        "current_stage": "str?",
        "recent_activity": "list",
        "open_items": "list",
        "known_needs": "list",
        "missing_information": "list",
        "risk_flags": "list",
        "sources": "list",
    },
    "rm-next-best-action": {
        "client_id": "str",
        "recommended_action": "str",
        "reason": "str",
        "priority": "str",
        "required_information": "list",
        "suggested_next_question": "str",
        "evidence": "list",
        "signal_code": "str",
        "other_signals": "list",
        "sources": "list",
    },
    "rm-opportunity-review": {
        "opportunity_id": "str",
        "client_id": "str",
        "stage_assessment": "str",
        "aging": "dict",
        "conversion_risk": "str",
        "missing_actions": "list",
        "recommended_actions": "list",
        "sources": "list",
    },
    "rm-followup-draft": {
        "client_id": "str",
        "draft": "str",
        "supporting_facts": "list",
        "requires_human_review": "bool",
        "delivery_status": "str",
        "approval_state": "str",
        "based_on_signal": "str",
        "sources": "list",
    },
}
