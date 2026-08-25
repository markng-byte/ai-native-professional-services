"""
Deterministic recommendation heuristics for the RM Co-pilot.

Decision D4/D5: RM recommendations are **rule-based, not LLM-generated**. Every
recommendation carries the evidence that triggered it, so the RM can audit *why*
it was made — and so the rules themselves remain Layer-1/Layer-3 gate-able. An
LLM may later narrate these results, but must never originate them (§12).

The rules are ordered by severity. The first matching rule wins, and the
remaining matches are still reported as ``other_signals`` so nothing is hidden
from the RM.

Every threshold these rules apply — stage SLAs, the stale-activity window, the
renewal window and the high-value line — is loaded from ``config/thresholds.json``
via ``src/policy``. They are firm advice policy, not constants, so the firm can
change what the co-pilot recommends without a code change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Decision windows come from config/thresholds.json (firm advice policy), not
# from constants here. See src/policy/thresholds.py.
import policy as _policy

PRIORITY_CRITICAL = "CRITICAL"
PRIORITY_HIGH = "HIGH"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_LOW = "LOW"


@dataclass
class Signal:
    """One detected condition, with the evidence that produced it."""
    code: str
    priority: str
    action: str
    reason: str
    evidence: List[str] = field(default_factory=list)
    required_information: List[str] = field(default_factory=list)
    next_question: Optional[str] = None

    def as_dict(self) -> Dict:
        return {
            "code": self.code,
            "priority": self.priority,
            "action": self.action,
            "reason": self.reason,
            "evidence": list(self.evidence),
        }


_PRIORITY_RANK = {
    PRIORITY_CRITICAL: 0,
    PRIORITY_HIGH: 1,
    PRIORITY_MEDIUM: 2,
    PRIORITY_LOW: 3,
}


def detect_signals(facts: Dict) -> List[Signal]:
    """Evaluate every rule against assembled facts.

    ``facts`` is built by the workflow layer from capability results only — this
    function performs no I/O and invents nothing.
    """
    _p = _policy.load()
    signals: List[Signal] = []

    client_id = facts.get("client_id")
    flags = facts.get("compliance_flags") or []
    documents = facts.get("documents") or []
    tasks = facts.get("open_tasks") or []
    renewals = facts.get("renewals") or []
    opportunities = facts.get("open_opportunities") or []
    days_since_activity = facts.get("days_since_last_activity")
    missing_info = facts.get("missing_information") or []

    # --- 1. Compliance exposure (CRITICAL) --------------------------------
    if flags:
        types = ", ".join(f.get("type", "FLAG") for f in flags)
        signals.append(Signal(
            code="COMPLIANCE_FLAG_OPEN",
            priority=PRIORITY_CRITICAL,
            action="Escalate to Compliance before progressing the relationship",
            reason=(
                f"{len(flags)} open compliance flag(s) on {client_id}: {types}. "
                "Firm policy blocks client-facing progression until cleared."
            ),
            evidence=[f"open_compliance_flags={types}"],
            next_question="Has Compliance cleared the open flag, or is a waiver documented?",
        ))

    expired = [d for d in documents if d.get("status") == "EXPIRED"]
    if expired:
        names = ", ".join(d["doc_type"] for d in expired)
        signals.append(Signal(
            code="DOCUMENT_EXPIRED",
            priority=PRIORITY_CRITICAL,
            action="Collect the expired KYC document(s) before any further service delivery",
            reason=f"Expired document(s) on file: {names}.",
            evidence=[f"expired_documents={names}"],
            required_information=[f"current {d['doc_type']}" for d in expired],
            next_question="Can the client provide a certified replacement this week?",
        ))

    # --- 2. Overdue commitments (HIGH) ------------------------------------
    overdue = [t for t in tasks if t.get("is_overdue")]
    if overdue:
        worst = min(overdue, key=lambda t: t["due_in_days"])
        signals.append(Signal(
            code="TASK_OVERDUE",
            priority=PRIORITY_HIGH,
            action=f"Clear the overdue task: {worst['title']}",
            reason=(
                f"{len(overdue)} task(s) overdue; the oldest is "
                f"{abs(worst['due_in_days'])} day(s) past due."
            ),
            evidence=[f"{t['task_id']} overdue by {abs(t['due_in_days'])}d" for t in overdue],
        ))

    # --- 3. Stalled pipeline (HIGH) ---------------------------------------
    for opp in opportunities:
        aging = opp.get("aging") or {}
        if aging.get("conversion_risk") == "HIGH":
            signals.append(Signal(
                code="OPPORTUNITY_STALLED",
                priority=PRIORITY_HIGH,
                action=f"Re-engage or escalate stalled opportunity {opp['opportunity_id']}",
                reason=(
                    f"{opp['opportunity_id']} shows HIGH conversion risk — {aging.get('basis')}"
                ),
                evidence=[f"{opp['opportunity_id']}: {aging.get('basis')}"],
                next_question="What is the specific blocker preventing this from closing?",
            ))

    # --- 4. Commercial conflict signals (HIGH) ----------------------------
    for opp in opportunities:
        close_in = opp.get("expected_close_in_days")
        if close_in is not None and close_in < 0:
            signals.append(Signal(
                code="CRM_DATA_CONFLICT",
                priority=PRIORITY_HIGH,
                action=f"Reconcile CRM data for {opp['opportunity_id']}",
                reason=(
                    f"{opp['opportunity_id']} is still open at stage {opp.get('stage')} "
                    f"but its expected close date passed {abs(close_in)} day(s) ago. "
                    "The record contradicts itself and cannot be trusted for forecasting."
                ),
                evidence=[
                    f"stage={opp.get('stage')} (open)",
                    f"expected_close_in_days={close_in} (past)",
                ],
                required_information=["revised expected close date", "current stage"],
                next_question="Should this opportunity be re-dated, re-staged, or closed out?",
            ))

    # --- 5. Renewal pressure (HIGH / MEDIUM) ------------------------------
    urgent = [r for r in renewals if r.get("is_urgent")]
    if urgent:
        soonest = min(urgent, key=lambda r: r["renewal_in_days"])
        signals.append(Signal(
            code="RENEWAL_DUE",
            priority=(PRIORITY_HIGH if soonest["renewal_in_days"]
                      <= _p.urgent_renewal_high_priority_days else PRIORITY_MEDIUM),
            action=f"Confirm renewal for {soonest['service_type']}",
            reason=(
                f"{len(urgent)} renewal(s) inside the {_p.urgent_renewal_days}-day window; "
                f"the soonest is {soonest['service_type']} in {soonest['renewal_in_days']} day(s)."
            ),
            evidence=[f"{r['engagement_id']} due in {r['renewal_in_days']}d" for r in urgent],
        ))

    # --- 6. Qualification gaps (MEDIUM) -----------------------------------
    missing_docs = [d for d in documents if d.get("status") == "MISSING"]
    if missing_docs:
        names = ", ".join(d["doc_type"] for d in missing_docs)
        signals.append(Signal(
            code="DOCUMENT_MISSING",
            priority=PRIORITY_MEDIUM,
            action="Request the outstanding onboarding document(s)",
            reason=f"Required document(s) not yet on file: {names}.",
            evidence=[f"missing_documents={names}"],
            required_information=[d["doc_type"] for d in missing_docs],
            next_question="Which documents can the client supply first?",
        ))

    # Only a qualification gap if there is actually a live opportunity to
    # qualify. "No opportunity on record" is the absence of a deal, not missing
    # detail about one, and must not produce a "qualify the opportunity" action.
    if missing_info and opportunities:
        signals.append(Signal(
            code="INSUFFICIENT_INFORMATION",
            priority=PRIORITY_MEDIUM,
            action="Qualify the opportunity before proposing commercial terms",
            reason=(
                "Key qualification data is absent, so any recommendation would be "
                f"speculative. Gaps: {'; '.join(missing_info)}."
            ),
            evidence=list(missing_info),
            required_information=list(missing_info),
            next_question="What is the client's intended structure, budget and timeline?",
        ))

    # --- 7. Engagement decay (MEDIUM) -------------------------------------
    if days_since_activity is None and opportunities:
        signals.append(Signal(
            code="NO_ACTIVITY_HISTORY",
            priority=PRIORITY_MEDIUM,
            action="Make first substantive contact and log it",
            reason="No interaction history exists for this client.",
            evidence=["days_since_last_activity=None"],
        ))
    elif days_since_activity is not None and days_since_activity > _p.stale_activity_days:
        high_value = [o for o in opportunities
                      if (o.get("amount") or 0) >= _p.high_value_amount]
        if high_value:
            names = ", ".join(o["opportunity_id"] for o in high_value)
            signals.append(Signal(
                code="HIGH_VALUE_GOING_COLD",
                priority=PRIORITY_HIGH,
                action=f"Re-engage now — high-value opportunity with no recent contact ({names})",
                reason=(
                    f"No logged contact for {days_since_activity} days while "
                    f"{names} carries a value at or above {_p.high_value_amount:,.0f}."
                ),
                evidence=[f"days_since_last_activity={days_since_activity}",
                          f"high_value_opportunities={names}"],
            ))
        else:
            signals.append(Signal(
                code="ACTIVITY_STALE",
                priority=PRIORITY_MEDIUM,
                action="Schedule a check-in — the relationship has gone quiet",
                reason=f"No logged contact for {days_since_activity} days.",
                evidence=[f"days_since_last_activity={days_since_activity}"],
            ))

    # --- 8. Healthy default (LOW) -----------------------------------------
    if not signals:
        if opportunities:
            opp = opportunities[0]
            signals.append(Signal(
                code="ADVANCE_STAGE",
                priority=PRIORITY_LOW,
                action=f"Progress {opp['opportunity_id']} to the next stage",
                reason=(
                    f"No risk signals detected; {opp['opportunity_id']} is within its "
                    "stage SLA with current documentation and no overdue tasks."
                ),
                evidence=[f"{opp['opportunity_id']}: {(opp.get('aging') or {}).get('basis', 'within SLA')}"],
                next_question="Is the client ready to receive the engagement letter?",
            ))
        elif facts.get("status") in ("ARCHIVED", "INACTIVE"):
            # An off-boarded client has no pipeline to advance. Recommending
            # commercial action here would be a fabricated opportunity.
            signals.append(Signal(
                code="NO_OPEN_OPPORTUNITY",
                priority=PRIORITY_LOW,
                action="No action — client is off-boarded",
                reason=(
                    f"{client_id} has status {facts.get('status')} and no open "
                    "opportunity. There is no pipeline to progress."
                ),
                evidence=[f"status={facts.get('status')}", "open_opportunities=0"],
                next_question="Should this client be considered for reactivation?",
            ))
        else:
            signals.append(Signal(
                code="NO_OPEN_OPPORTUNITY",
                priority=PRIORITY_LOW,
                action="Explore a new mandate — no open opportunity exists",
                reason="The client is active but has no open opportunity on record.",
                evidence=["open_opportunities=0"],
                next_question="Which additional services would be relevant this year?",
            ))

    signals.sort(key=lambda s: _PRIORITY_RANK.get(s.priority, 9))
    return signals
