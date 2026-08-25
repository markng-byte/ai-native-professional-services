"""
Template-based follow-up drafting.

Decision D5: **no LLM in the v1 core.** Drafts are rendered from templates over
structured evidence, so the output is deterministic, reviewable and testable.
An LLM may later re-phrase a draft, but the facts must continue to originate
here (§12: the model narrates, it does not originate).

Every draft is internal-review output. It is never addressed-and-sent: the
caller receives ``delivery_status = DRAFT_NOT_SENT`` and
``requires_human_review = True`` (governance rows 4/5/7 — the RM reviews and
sends; the agent does not).

Placeholders are left **visible** (``[CONTACT NAME]``) rather than guessed, so a
reviewer can see exactly what the system did not know.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

_SIGNAL_OPENERS = {
    "COMPLIANCE_FLAG_OPEN":
        "I am pausing progress on your file until an internal compliance review completes.",
    "DOCUMENT_EXPIRED":
        "One of the identification documents we hold for you has expired.",
    "DOCUMENT_MISSING":
        "To progress your file we still need a small number of onboarding documents.",
    "TASK_OVERDUE":
        "I owe you an update, and I want to make sure nothing is waiting on us.",
    "OPPORTUNITY_STALLED":
        "I wanted to check in — our last exchange was some time ago and I would like to "
        "understand where things stand on your side.",
    "CRM_DATA_CONFLICT":
        "I am reviewing our records for your mandate and want to confirm the current timing.",
    "RENEWAL_DUE":
        "Your current engagement is approaching its renewal date.",
    "HIGH_VALUE_GOING_COLD":
        "It has been a while since we last spoke, and I would like to pick this back up.",
    "ACTIVITY_STALE":
        "It has been a while since we last spoke — I wanted to reconnect.",
    "INSUFFICIENT_INFORMATION":
        "Before I put firm numbers in front of you, I would like to confirm a few details.",
    "NO_ACTIVITY_HISTORY":
        "Thank you for your interest — I would like to introduce myself and understand your needs.",
    "ADVANCE_STAGE":
        "Thank you for the discussion so far. I think we are ready for the next step.",
    "NO_OPEN_OPPORTUNITY":
        "I wanted to touch base about how else we might support you this year.",
}


def render_followup(facts: Dict, signal) -> Tuple[str, List[Dict]]:
    """Render a follow-up draft plus the facts that justify it.

    Returns ``(draft_text, supporting_facts)``. Each supporting fact names the
    capability it came from, so an RM can audit every claim in the draft.
    """
    legal_name = facts.get("legal_name") or "[CLIENT NAME]"
    opener = _SIGNAL_OPENERS.get(
        signal.code, "I wanted to follow up on your file."
    )

    supporting_facts: List[Dict] = []

    def cite(label: str, value, source: str):
        supporting_facts.append({"fact": label, "value": value, "source": source})

    cite("client", legal_name, "get_rm_client_context")
    cite("jurisdiction", facts.get("jurisdiction"), "get_rm_client_context")
    cite("triggering_signal", signal.code, "rm.heuristics")
    cite("signal_reason", signal.reason, "rm.heuristics")

    body_lines: List[str] = []

    for opp in facts.get("open_opportunities") or []:
        cite("open_opportunity", f"{opp['opportunity_id']} — {opp['name']} ({opp['stage']})",
             "get_opportunity_context")
    overdue = [t for t in facts.get("open_tasks") or [] if t.get("is_overdue")]
    for t in overdue:
        cite("overdue_task", f"{t['task_id']} — {t['title']}", "get_open_tasks")

    outstanding = [d for d in facts.get("documents") or []
                   if d.get("status") in ("MISSING", "EXPIRED")]
    if outstanding:
        names = ", ".join(f"{d['doc_type']} ({d['status'].lower()})" for d in outstanding)
        body_lines.append(f"Outstanding documentation: {names}.")
        cite("outstanding_documents", names, "get_client_documents")

    urgent_renewals = [r for r in facts.get("renewals") or [] if r.get("is_urgent")]
    if urgent_renewals:
        r = urgent_renewals[0]
        body_lines.append(
            f"Your {r['service_type'].replace('_', ' ').lower()} engagement is due for "
            f"renewal in {r['renewal_in_days']} days."
        )
        cite("urgent_renewal", f"{r['engagement_id']} in {r['renewal_in_days']}d",
             "get_renewal_status")

    if signal.required_information:
        body_lines.append(
            "To move forward I would be grateful if you could confirm: "
            + "; ".join(signal.required_information) + "."
        )

    question = signal.next_question
    if question:
        body_lines.append(question)

    gaps = facts.get("missing_information") or []
    if gaps:
        cite("known_information_gaps", gaps, "rm-client-summary")

    body = "\n\n".join(body_lines) if body_lines else (
        "Please let me know a convenient time to speak."
    )

    draft = (
        f"Subject: Follow-up — {legal_name}\n\n"
        f"Dear [CONTACT NAME],\n\n"
        f"{opener}\n\n"
        f"{body}\n\n"
        f"Kind regards,\n"
        f"[RM NAME]\n"
        f"[FIRM NAME]\n\n"
        f"--- INTERNAL: DRAFT ONLY — NOT SENT. Requires RM review and approval "
        f"before any client delivery. ---"
    )
    return draft, supporting_facts
