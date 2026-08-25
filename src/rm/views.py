"""
RM surface view models.

**Pure functions. No Streamlit import. No business logic.**

Each function takes a workflow envelope and returns a render-ready dictionary.
Two properties are deliberate and are enforced by ``tests/test_rm_views.py``:

1. **Nothing is re-derived.** A view copies what the workflow decided; it never
   recomputes priority, risk, ageing, or a recommendation. Re-deriving values in
   a presentation layer is precisely how the triplication documented in the
   Phase 0 audit began, and this module is where that would start again.
2. **Nothing is dropped.** ``missing_information`` and ``other_signals`` are
   carried through, because a co-pilot that quietly hides what it does not know —
   or the risks it decided not to lead with — is worse than one that says nothing.

The only transformation permitted here is **presentation**: mapping a priority to
a badge glyph, ordering sections, truncating a list for display while reporting
that it was truncated. Those are styling decisions, not judgements.
"""

from __future__ import annotations

from typing import Dict, List, Optional

# --- presentation lookups (styling only, never a judgement) ----------------

_PRIORITY_BADGE = {
    "CRITICAL": {"glyph": "🔴", "label": "CRITICAL", "tone": "critical"},
    "HIGH": {"glyph": "🟠", "label": "HIGH", "tone": "high"},
    "MEDIUM": {"glyph": "🟡", "label": "MEDIUM", "tone": "medium"},
    "LOW": {"glyph": "🟢", "label": "LOW", "tone": "low"},
}
_UNKNOWN_BADGE = {"glyph": "⚪", "label": "UNKNOWN", "tone": "unknown"}

_RISK_BADGE = {
    "HIGH": {"glyph": "🔴", "tone": "critical"},
    "MEDIUM": {"glyph": "🟡", "tone": "medium"},
    "LOW": {"glyph": "🟢", "tone": "low"},
}

_APPROVAL_TONE = {
    "DRAFTED": "muted",
    "PENDING_REVIEW": "medium",
    "APPROVED": "low",
    "REJECTED": "critical",
}


def priority_badge(priority: Optional[str]) -> Dict:
    return _PRIORITY_BADGE.get(priority or "", _UNKNOWN_BADGE)


def risk_badge(risk: Optional[str]) -> Dict:
    return _RISK_BADGE.get(risk or "", {"glyph": "⚪", "tone": "unknown"})


# --- envelope plumbing -----------------------------------------------------

def audit_ribbon(envelope: Dict) -> Dict:
    """Identifiers an RM (or an auditor) can quote. Always shown, never hidden."""
    audit = envelope.get("audit") or {}
    return {
        "correlation_id": envelope.get("correlation_id"),
        "audit_ref": audit.get("audit_ref"),
        "capability": envelope.get("capability"),
        "data_source": audit.get("data_source"),
        "actor_id": audit.get("actor_id"),
        "authorized": (audit.get("authorization") or {}).get("allowed"),
        "authorization_reason": (audit.get("authorization") or {}).get("reason"),
        "timestamp": audit.get("timestamp"),
    }


def error_view(envelope: Dict) -> Dict:
    """Render a failure honestly — including an authorization denial.

    The surface must never substitute a friendly empty state for a denial: an
    RM who is told "no data" when they were actually refused access would draw
    a false conclusion about the client.
    """
    err = envelope.get("error") or {}
    code = err.get("code")
    is_denial = code == "ERR_NOT_AUTHORIZED"
    return {
        "kind": "error",
        "code": code,
        "message": err.get("message"),
        "is_authorization_denial": is_denial,
        "headline": "Not authorised" if is_denial else "Could not complete this request",
        "audit": audit_ribbon(envelope),
    }


def _guard(envelope: Dict) -> Optional[Dict]:
    """Return an error view if the envelope failed, else None."""
    if not envelope.get("ok"):
        return error_view(envelope)
    return None


# --- views -----------------------------------------------------------------

def search_results_view(envelope: Dict) -> Dict:
    failure = _guard(envelope)
    if failure:
        return failure
    result = envelope["result"]
    matches = result.get("matches") or []
    return {
        "kind": "search_results",
        "query": result.get("query"),
        "match_count": result.get("match_count"),
        "matches": [
            {
                "client_id": m.get("client_id"),
                "legal_name": m.get("legal_name"),
                "jurisdiction": m.get("jurisdiction"),
                "status": m.get("status"),
                "risk_rating": m.get("risk_rating"),
                "risk": risk_badge(m.get("risk_rating")),
            }
            for m in matches
        ],
        # An empty result set is not the same as "no such client": the search is
        # authorization-filtered, so say so rather than implying non-existence.
        "empty_note": (
            "No clients you are assigned to match this search. Clients assigned "
            "to another RM are not shown."
            if not matches else None
        ),
        "audit": audit_ribbon(envelope),
    }


def client_summary_view(envelope: Dict) -> Dict:
    failure = _guard(envelope)
    if failure:
        return failure
    r = envelope["result"]
    return {
        "kind": "client_summary",
        "client_id": r.get("client_id"),
        "headline": r.get("client_summary"),
        "current_stage": r.get("current_stage"),
        "opportunities": [
            {
                "opportunity_id": o.get("opportunity_id"),
                "name": o.get("name"),
                "stage": o.get("stage"),
                "amount": o.get("amount"),
                "currency": o.get("currency"),
                "conversion_risk": o.get("conversion_risk"),
                "is_stalled": o.get("is_stalled"),
                "risk": risk_badge(o.get("conversion_risk")),
            }
            for o in r.get("opportunity_summary") or []
        ],
        "risk_flags": [
            {
                "code": f.get("code"),
                "priority": f.get("priority"),
                "action": f.get("action"),
                "reason": f.get("reason"),
                "evidence": f.get("evidence") or [],
                "badge": priority_badge(f.get("priority")),
            }
            for f in r.get("risk_flags") or []
        ],
        "open_items": r.get("open_items") or [],
        "known_needs": r.get("known_needs") or [],
        "recent_activity": r.get("recent_activity") or [],
        # Shown prominently, never collapsed away.
        "missing_information": r.get("missing_information") or [],
        "sources": r.get("sources") or [],
        "audit": audit_ribbon(envelope),
    }


def next_action_view(envelope: Dict) -> Dict:
    failure = _guard(envelope)
    if failure:
        return failure
    r = envelope["result"]
    return {
        "kind": "next_action",
        "client_id": r.get("client_id"),
        "recommended_action": r.get("recommended_action"),
        "reason": r.get("reason"),
        "priority": r.get("priority"),
        "badge": priority_badge(r.get("priority")),
        "signal_code": r.get("signal_code"),
        "evidence": r.get("evidence") or [],
        "required_information": r.get("required_information") or [],
        "suggested_next_question": r.get("suggested_next_question"),
        # Signals that lost the ranking are still surfaced.
        "other_signals": [
            {
                "code": s.get("code"),
                "priority": s.get("priority"),
                "action": s.get("action"),
                "reason": s.get("reason"),
                "evidence": s.get("evidence") or [],
                "badge": priority_badge(s.get("priority")),
            }
            for s in r.get("other_signals") or []
        ],
        "sources": r.get("sources") or [],
        "audit": audit_ribbon(envelope),
    }


def opportunity_review_view(envelope: Dict) -> Dict:
    failure = _guard(envelope)
    if failure:
        return failure
    r = envelope["result"]
    aging = r.get("aging") or {}
    return {
        "kind": "opportunity_review",
        "opportunity_id": r.get("opportunity_id"),
        "client_id": r.get("client_id"),
        "stage_assessment": r.get("stage_assessment"),
        "conversion_risk": r.get("conversion_risk"),
        "risk": risk_badge(r.get("conversion_risk")),
        "aging": {
            "stage": aging.get("stage"),
            "days_in_stage": aging.get("days_in_stage"),
            "sla_days": aging.get("sla_days"),
            "over_sla_by_days": aging.get("over_sla_by_days"),
            "is_stalled": aging.get("is_stalled"),
            # The explainable basis, not just a score...
            "basis": aging.get("basis"),
            # ...and whose rule produced it. An RM should be able to see that a
            # risk band is firm policy with an owner, not an oracle.
            "policy_source": aging.get("policy_source"),
        },
        "missing_actions": r.get("missing_actions") or [],
        "recommended_actions": [
            {
                "code": a.get("code"),
                "priority": a.get("priority"),
                "action": a.get("action"),
                "reason": a.get("reason"),
                "evidence": a.get("evidence") or [],
                "badge": priority_badge(a.get("priority")),
            }
            for a in r.get("recommended_actions") or []
        ],
        "sources": r.get("sources") or [],
        "audit": audit_ribbon(envelope),
    }


def draft_view(envelope: Dict, approval: Optional[Dict] = None,
               gate: Optional[Dict] = None) -> Dict:
    """Render a draft with its approval state and the gate's verdict.

    ``approval`` is an ``ApprovalRecord.as_dict()``; ``gate`` is the decision
    returned by ``validation.deliver``. Both are optional so the same view
    renders a fresh draft, a pending one, and a decided one.
    """
    failure = _guard(envelope)
    if failure:
        return failure
    r = envelope["result"]

    state = (approval or {}).get("state") or r.get("approval_state")
    blocked_reasons = list((gate or {}).get("violations") or [])
    delivered = bool((gate or {}).get("delivered"))

    return {
        "kind": "draft",
        "client_id": r.get("client_id"),
        "draft": r.get("draft"),
        "supporting_facts": r.get("supporting_facts") or [],
        "based_on_signal": r.get("based_on_signal"),
        "requires_human_review": r.get("requires_human_review"),
        "delivery_status": r.get("delivery_status"),
        "approval_state": state,
        "approval_tone": _APPROVAL_TONE.get(state or "", "muted"),
        "approval_id": (approval or {}).get("approval_id"),
        "required_role": (approval or {}).get("required_role"),
        "decided_by": (approval or {}).get("decided_by"),
        "decision_justification": (approval or {}).get("decision_justification"),
        "events": (approval or {}).get("events") or [],
        "gate_delivered": delivered,
        "gate_status": (gate or {}).get("delivery_status"),
        "blocked_reasons": blocked_reasons,
        # Always true in v1: no send surface exists anywhere in the system.
        "never_sent_notice": (
            "This draft has not been sent. Approval records a decision; it does "
            "not transmit anything."
        ),
        "sources": r.get("sources") or [],
        "audit": audit_ribbon(envelope),
    }


def workspace_view(summary_env: Dict, action_env: Dict) -> Dict:
    """Compose the two client-level panels into one workspace payload."""
    return {
        "kind": "workspace",
        "summary": client_summary_view(summary_env),
        "next_action": next_action_view(action_env),
    }
