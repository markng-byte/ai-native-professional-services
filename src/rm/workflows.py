"""
Tier 2 RM Co-pilot workflows (recommend / draft).

These compose **Tier 1 capability tools only** — they never touch an adapter, a
CRM, or a data fixture directly. Every fact in a workflow output is traceable to
a capability result, and every capability result carries its own audit record.

    RM -> Tier 2 workflow -> Tier 1 capability -> CRMAdapter -> fixtures

Design rules enforced here:
  * **Deterministic** (decisions D4/D5) — recommendations come from the rule
    engine in :mod:`rm.heuristics`; no LLM originates a fact or a judgement.
  * **Grounded** — outputs cite the capabilities and signals behind them.
  * **Honest about gaps** (§11) — unknowns are reported, never invented.
  * **Human-gated** (§9, governance rows 4/5/7) — drafts are returned for review
    and are never sent. ``requires_human_review`` is always true on drafts.
  * **Authorization propagates** — a denial inside any capability aborts the
    workflow with that error rather than returning a partial answer.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from capabilities import CAPABILITIES
from capabilities.contracts import (
    error_envelope,
    make_audit,
    new_correlation_id,
    ok_envelope,
)
from capabilities.errors import ERR_VALIDATION
from crm.models import stage_is_open
from rm.drafting import render_followup
from rm.heuristics import detect_signals


def _fail(workflow: str, correlation_id: str, payload: Dict, code: str, message: str) -> Dict:
    actor = (payload.get("actor") or {})
    audit = make_audit(
        capability=workflow, correlation_id=correlation_id,
        actor_type=actor.get("actor_type", "RM") if actor else None,
        actor_id=actor.get("rm_id") or actor.get("actor_id") if actor else None,
        status="ERROR",
        authorization={"allowed": False, "reason": "workflow precondition failed"},
    )
    return error_envelope(workflow, correlation_id, code, message, audit)


def _relay_failure(workflow: str, correlation_id: str, envelope: Dict) -> Dict:
    """Re-emit a capability failure under the workflow's own name.

    The originating capability's audit record is preserved verbatim so the
    denial (or not-found) remains traceable to where it actually occurred.
    """
    audit = dict(envelope.get("audit") or {})
    audit["relayed_from_capability"] = envelope.get("capability")
    audit["capability"] = workflow
    err = envelope.get("error") or {}
    return error_envelope(
        workflow, correlation_id,
        err.get("code", ERR_VALIDATION),
        err.get("message", "upstream capability failed"),
        audit,
    )


def _call(cap: str, actor: Dict, correlation_id: str, **params) -> Dict:
    return CAPABILITIES[cap]({"actor": actor, "correlation_id": correlation_id, **params})


def _gather_client_facts(actor: Dict, correlation_id: str, client_id: str) -> Tuple[Optional[Dict], Optional[Dict]]:
    """Assemble every fact the heuristics need for a client.

    Returns ``(facts, failure_envelope)`` — exactly one is non-None.
    """
    calls = {
        "context": ("get_rm_client_context", {"client_id": client_id}),
        "history": ("get_client_history", {"client_id": client_id}),
        "tasks": ("get_open_tasks", {"client_id": client_id}),
        "documents": ("get_client_documents", {"client_id": client_id}),
        "renewals": ("get_renewal_status", {"client_id": client_id}),
        "engagements": ("get_client_engagements", {"client_id": client_id}),
    }
    results: Dict[str, Dict] = {}
    for key, (cap, params) in calls.items():
        env = _call(cap, actor, correlation_id, **params)
        if not env["ok"]:
            return None, env
        results[key] = env["result"]

    ctx = results["context"]

    # Enrich each open opportunity with its full context (incl. ageing).
    enriched: List[Dict] = []
    missing_information = list(ctx.get("missing_information") or [])
    for brief in ctx.get("open_opportunities") or []:
        env = _call("get_opportunity_context", actor, correlation_id,
                    opportunity_id=brief["opportunity_id"])
        if not env["ok"]:
            return None, env
        enriched.append(env["result"])
        for gap in env["result"].get("missing_information") or []:
            entry = f"{brief['opportunity_id']}: {gap}"
            if entry not in missing_information:
                missing_information.append(entry)

    facts = {
        "client_id": client_id,
        "legal_name": ctx.get("legal_name"),
        "jurisdiction": ctx.get("jurisdiction"),
        "risk_rating": ctx.get("risk_rating"),
        "status": ctx.get("status"),
        "compliance_flags": ctx.get("compliance_flags") or [],
        "skill_evidence": ctx.get("skill_evidence") or {},
        "open_opportunities": enriched,
        "activities": results["history"].get("activities") or [],
        "days_since_last_activity": results["history"].get("days_since_last_activity"),
        "open_tasks": results["tasks"].get("tasks") or [],
        "documents": results["documents"].get("documents") or [],
        "renewals": results["renewals"].get("renewals") or [],
        "engagements": results["engagements"].get("engagements") or [],
        "missing_information": missing_information,
        "sources": sorted({cap for cap, _ in calls.values()} | {"get_opportunity_context"}),
    }
    return facts, None


def _begin(workflow: str, payload: Dict, required: str):
    correlation_id = new_correlation_id(payload)
    actor = payload.get("actor")
    if not isinstance(actor, dict):
        return None, _fail(workflow, correlation_id, payload, ERR_VALIDATION,
                           "actor is required: expected {'actor': {'rm_id': '<RM-ID>'}}")
    value = payload.get(required)
    if not value or not isinstance(value, str):
        return None, _fail(workflow, correlation_id, payload, ERR_VALIDATION,
                           f"{required} is required and must be a string")
    return (correlation_id, actor, value), None


def _ok(workflow: str, correlation_id: str, actor: Dict, result: Dict,
        client_id=None, opportunity_id=None) -> Dict:
    audit = make_audit(
        capability=workflow, correlation_id=correlation_id,
        actor_type=actor.get("actor_type", "RM"),
        actor_id=actor.get("rm_id") or actor.get("actor_id"),
        status="OK", authorization={"allowed": True, "reason": "authorized"},
        client_id=client_id, opportunity_id=opportunity_id,
    )
    return ok_envelope(workflow, correlation_id, result, audit)


# ---------------------------------------------------------------------------
# rm-client-summary
# ---------------------------------------------------------------------------

def rm_client_summary(payload: Dict) -> Dict:
    """The RM's working picture of a client: state, risks, gaps, open items."""
    wf = "rm-client-summary"
    started, failure = _begin(wf, payload, "client_id")
    if failure:
        return failure
    correlation_id, actor, client_id = started

    facts, failure = _gather_client_facts(actor, correlation_id, client_id)
    if failure:
        return _relay_failure(wf, correlation_id, failure)

    opps = facts["open_opportunities"]
    signals = detect_signals(facts)

    opportunity_summary = [
        {
            "opportunity_id": o["opportunity_id"], "name": o["name"], "stage": o["stage"],
            "amount": o["amount"], "currency": o["currency"],
            "conversion_risk": (o.get("aging") or {}).get("conversion_risk"),
            "is_stalled": (o.get("aging") or {}).get("is_stalled"),
        }
        for o in opps
    ]

    open_items = (
        [{"type": "TASK", "ref": t["task_id"], "detail": t["title"],
          "is_overdue": t["is_overdue"]} for t in facts["open_tasks"]]
        + [{"type": "RENEWAL", "ref": r["engagement_id"],
            "detail": f"{r['service_type']} renewal in {r['renewal_in_days']}d",
            "is_overdue": False} for r in facts["renewals"] if r["is_urgent"]]
        + [{"type": "DOCUMENT", "ref": d["doc_id"],
            "detail": f"{d['doc_type']} is {d['status']}", "is_overdue": d["status"] == "EXPIRED"}
           for d in facts["documents"] if d["status"] in ("EXPIRED", "MISSING", "EXPIRING")]
    )

    known_needs = sorted({e["service_type"] for e in facts["engagements"]
                          if e["status"] == "ACTIVE"}
                         | {o["service_type"] for o in opps if o["service_type"] != "UNKNOWN"})

    risk_flags = [s.as_dict() for s in signals
                  if s.priority in ("CRITICAL", "HIGH")]

    stages = [o["stage"] for o in opps]
    client_summary = (
        f"{facts['legal_name']} ({facts['jurisdiction']}) — {facts['status']}, "
        f"risk {facts['risk_rating']}. "
        f"{len(opps)} open opportunit{'y' if len(opps) == 1 else 'ies'}, "
        f"{len(facts['open_tasks'])} open task(s), "
        f"{len(risk_flags)} elevated risk signal(s)."
    )

    result = {
        "client_id": client_id,
        "client_summary": client_summary,
        "opportunity_summary": opportunity_summary,
        "current_stage": stages[0] if len(set(stages)) == 1 and stages else None,
        "recent_activity": facts["activities"][:5],
        "open_items": open_items,
        "known_needs": known_needs,
        "missing_information": facts["missing_information"],
        "risk_flags": risk_flags,
        "sources": facts["sources"],
    }
    return _ok(wf, correlation_id, actor, result, client_id=client_id)


# ---------------------------------------------------------------------------
# rm-next-best-action
# ---------------------------------------------------------------------------

def rm_next_best_action(payload: Dict) -> Dict:
    """Recommend the single highest-value next action, with its evidence."""
    wf = "rm-next-best-action"
    started, failure = _begin(wf, payload, "client_id")
    if failure:
        return failure
    correlation_id, actor, client_id = started

    facts, failure = _gather_client_facts(actor, correlation_id, client_id)
    if failure:
        return _relay_failure(wf, correlation_id, failure)

    signals = detect_signals(facts)
    top = signals[0]

    result = {
        "client_id": client_id,
        "recommended_action": top.action,
        "reason": top.reason,
        "priority": top.priority,
        "required_information": top.required_information,
        "suggested_next_question": top.next_question or
            "What is the single blocker preventing this from moving forward?",
        "evidence": top.evidence,
        "signal_code": top.code,
        "other_signals": [s.as_dict() for s in signals[1:]],
        "sources": facts["sources"],
    }
    return _ok(wf, correlation_id, actor, result, client_id=client_id)


# ---------------------------------------------------------------------------
# rm-opportunity-review
# ---------------------------------------------------------------------------

def rm_opportunity_review(payload: Dict) -> Dict:
    """Assess one opportunity: stage health, ageing, risk, and what is missing."""
    wf = "rm-opportunity-review"
    started, failure = _begin(wf, payload, "opportunity_id")
    if failure:
        return failure
    correlation_id, actor, opportunity_id = started

    env = _call("get_opportunity_context", actor, correlation_id,
                opportunity_id=opportunity_id)
    if not env["ok"]:
        return _relay_failure(wf, correlation_id, env)
    opp = env["result"]
    aging = opp.get("aging") or {}

    tasks_env = _call("get_open_tasks", actor, correlation_id, client_id=opp["client_id"])
    if not tasks_env["ok"]:
        return _relay_failure(wf, correlation_id, tasks_env)
    open_tasks = [t for t in tasks_env["result"]["tasks"]
                  if t.get("opportunity_id") == opportunity_id]

    # Reuse the same rule engine, scoped to this one opportunity.
    signals = detect_signals({
        "client_id": opp["client_id"],
        "open_opportunities": [opp],
        "open_tasks": open_tasks,
        "missing_information": opp.get("missing_information") or [],
        "days_since_last_activity": (
            min((a["occurred_days_ago"] for a in opp.get("recent_activity") or []), default=None)
        ),
    })

    if aging.get("is_stalled"):
        stage_assessment = (
            f"STALLED — {opp['stage']} for {aging.get('days_in_stage')}d against a "
            f"{aging.get('sla_days')}d SLA ({aging.get('over_sla_by_days')}d over)."
        )
    else:
        stage_assessment = (
            f"HEALTHY — {opp['stage']} for {aging.get('days_in_stage')}d, within its "
            f"{aging.get('sla_days')}d SLA."
        )

    missing_actions: List[str] = []
    if not open_tasks:
        missing_actions.append("No open task owns the next step for this opportunity")
    for gap in opp.get("missing_information") or []:
        missing_actions.append(f"Capture: {gap}")

    # A record that contradicts itself cannot be trusted for forecasting;
    # reconciling it is a required action, not merely a suggestion.
    close_in = opp.get("expected_close_in_days")
    if close_in is not None and close_in < 0 and stage_is_open(opp["stage"]):
        missing_actions.append(
            f"Reconcile: expected close date passed {abs(close_in)}d ago while "
            f"stage is still {opp['stage']}"
        )

    result = {
        "opportunity_id": opportunity_id,
        "client_id": opp["client_id"],
        "stage_assessment": stage_assessment,
        "aging": aging,
        "conversion_risk": aging.get("conversion_risk"),
        "missing_actions": missing_actions,
        "recommended_actions": [s.as_dict() for s in signals],
        "sources": ["get_opportunity_context", "get_open_tasks"],
    }
    return _ok(wf, correlation_id, actor, result,
               client_id=opp["client_id"], opportunity_id=opportunity_id)


# ---------------------------------------------------------------------------
# rm-followup-draft
# ---------------------------------------------------------------------------

def rm_followup_draft(payload: Dict) -> Dict:
    """Draft an internal-review follow-up. Never sent; always human-gated."""
    wf = "rm-followup-draft"
    started, failure = _begin(wf, payload, "client_id")
    if failure:
        return failure
    correlation_id, actor, client_id = started

    facts, failure = _gather_client_facts(actor, correlation_id, client_id)
    if failure:
        return _relay_failure(wf, correlation_id, failure)

    signals = detect_signals(facts)
    draft, supporting_facts = render_followup(facts, signals[0])

    result = {
        "client_id": client_id,
        "draft": draft,
        "supporting_facts": supporting_facts,
        "requires_human_review": True,          # governance rows 4/5/7 — invariant
        "delivery_status": "DRAFT_NOT_SENT",
        "approval_state": "DRAFTED",            # Phase 4 will enforce the transition
        "based_on_signal": signals[0].code,
        "sources": facts["sources"],
    }
    return _ok(wf, correlation_id, actor, result, client_id=client_id)


RM_WORKFLOWS: Dict[str, Callable[[Dict], Dict]] = {
    "rm-client-summary": rm_client_summary,
    "rm-next-best-action": rm_next_best_action,
    "rm-opportunity-review": rm_opportunity_review,
    "rm-followup-draft": rm_followup_draft,
}
