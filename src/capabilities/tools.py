"""
Tier 1 (READ) business capability tools for the RM Co-pilot.

These are **business capabilities, not CRUD**. No agent is ever handed
``salesforce.query()`` / ``create()`` / ``update()`` / ``delete()``; it binds to
verbs like ``get_opportunity_context``. The contract must survive a change to
the underlying CRM object model (master prompt §8):

    RM Agent -> Business Capability Tool -> CRMAdapter -> (fixtures | Salesforce)

Every capability:
  * takes ``{"actor": {"rm_id": ...}, "correlation_id": ..., ...params}``,
  * returns the shared envelope from :mod:`capabilities.contracts`,
  * makes an explicit authorization decision (§21) recorded in the audit record,
  * reports **missing information explicitly** rather than inventing it (§11),
  * is fully deterministic — no LLM, no clock dependence (decisions D4/D5).

``get_rm_client_context`` *wraps* the gate-verified ``client-lookup`` skill
rather than re-implementing client resolution (decision D3, and §26's
prohibition on duplicated logic). The skill remains the source of truth; this
layer composes it with CRM transactional data.
"""

from __future__ import annotations

import sys
from typing import Callable, Dict, List, Optional

from capabilities import authz as authz_mod
from capabilities.contracts import (
    error_envelope,
    make_audit,
    new_correlation_id,
    ok_envelope,
)
from capabilities.errors import (
    ERR_CLIENT_NOT_FOUND,
    ERR_OPPORTUNITY_NOT_FOUND,
    ERR_VALIDATION,
)
from crm.adapters import get_adapter
from crm.models import assess_aging, stage_is_open

import policy as _policy

from skills import SKILLS  # gate-verified deterministic skills


# ---------------------------------------------------------------------------
# Shared request handling
# ---------------------------------------------------------------------------

def _begin(capability: str, payload: Dict):
    """Resolve correlation id, actor and adapter, or return a failure envelope.

    Returns ``(context, failure_envelope)`` — exactly one is non-None.
    """
    correlation_id = new_correlation_id(payload)
    adapter = get_adapter()

    actor = authz_mod.parse_actor(payload)
    if actor is None:
        audit = make_audit(
            capability=capability, correlation_id=correlation_id,
            actor_type=None, actor_id=None, status="ERROR",
            authorization={"allowed": False, "reason": "actor missing or malformed"},
            data_source=adapter.source_name,
        )
        return None, error_envelope(
            capability, correlation_id, ERR_VALIDATION,
            "actor is required: expected {'actor': {'rm_id': '<RM-ID>'}}", audit,
        )

    decision = authz_mod.authorize_actor_known(actor, adapter)
    if not decision.allowed:
        audit = make_audit(
            capability=capability, correlation_id=correlation_id,
            actor_type=actor.actor_type, actor_id=actor.actor_id, status="ERROR",
            authorization=decision.as_audit(), data_source=adapter.source_name,
        )
        return None, error_envelope(
            capability, correlation_id, decision.error_code, decision.reason, audit
        )

    return {"correlation_id": correlation_id, "actor": actor, "adapter": adapter}, None


def _resolve_client(capability: str, ctx: Dict, client_id: Optional[str]):
    """Fetch a client and authorize the actor against it.

    Returns ``(client, failure_envelope)`` — exactly one is non-None.
    """
    correlation_id, actor, adapter = ctx["correlation_id"], ctx["actor"], ctx["adapter"]

    if not client_id or not isinstance(client_id, str):
        audit = make_audit(
            capability=capability, correlation_id=correlation_id,
            actor_type=actor.actor_type, actor_id=actor.actor_id, status="ERROR",
            authorization={"allowed": True, "reason": "actor recognised"},
            data_source=adapter.source_name,
        )
        return None, error_envelope(
            capability, correlation_id, ERR_VALIDATION,
            "client_id is required and must be a string", audit,
        )

    client = adapter.get_client(client_id)
    if client is None:
        audit = make_audit(
            capability=capability, correlation_id=correlation_id,
            actor_type=actor.actor_type, actor_id=actor.actor_id, status="ERROR",
            authorization={"allowed": True, "reason": "actor recognised"},
            client_id=client_id, data_source=adapter.source_name,
        )
        return None, error_envelope(
            capability, correlation_id, ERR_CLIENT_NOT_FOUND,
            f"No client with id {client_id!r}.", audit,
        )

    decision = authz_mod.authorize_client_access(actor, client, adapter)
    if not decision.allowed:
        audit = make_audit(
            capability=capability, correlation_id=correlation_id,
            actor_type=actor.actor_type, actor_id=actor.actor_id, status="ERROR",
            authorization=decision.as_audit(), client_id=client_id,
            data_source=adapter.source_name,
        )
        return None, error_envelope(
            capability, correlation_id, decision.error_code, decision.reason, audit
        )

    return client, None


def _success(capability: str, ctx: Dict, result: Dict, *, client_id=None, opportunity_id=None):
    audit = make_audit(
        capability=capability, correlation_id=ctx["correlation_id"],
        actor_type=ctx["actor"].actor_type, actor_id=ctx["actor"].actor_id,
        status="OK", authorization={"allowed": True, "reason": "authorized"},
        client_id=client_id, opportunity_id=opportunity_id,
        data_source=ctx["adapter"].source_name,
    )
    return ok_envelope(capability, ctx["correlation_id"], result, audit)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _opp_brief(o) -> Dict:
    return {
        "opportunity_id": o.opportunity_id, "name": o.name, "stage": o.stage,
        "amount": o.amount, "currency": o.currency, "service_type": o.service_type,
        "days_in_stage": o.days_in_stage,
    }


def _activity(a) -> Dict:
    return {
        "activity_id": a.activity_id, "activity_type": a.activity_type,
        "subject": a.subject, "occurred_days_ago": a.occurred_days_ago,
        "actor": a.actor, "opportunity_id": a.opportunity_id,
    }


def _task(t) -> Dict:
    return {
        "task_id": t.task_id, "title": t.title, "status": t.status,
        "due_in_days": t.due_in_days, "is_overdue": t.status == "OPEN" and t.due_in_days < 0,
        "owner_rm_id": t.owner_rm_id, "opportunity_id": t.opportunity_id,
    }


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

def search_client(payload: Dict) -> Dict:
    """Find clients the requesting RM is permitted to see."""
    cap = "search_client"
    ctx, failure = _begin(cap, payload)
    if failure:
        return failure

    query = payload.get("query")
    if not isinstance(query, str) or not query.strip():
        audit = make_audit(
            capability=cap, correlation_id=ctx["correlation_id"],
            actor_type=ctx["actor"].actor_type, actor_id=ctx["actor"].actor_id,
            status="ERROR", authorization={"allowed": True, "reason": "actor recognised"},
            data_source=ctx["adapter"].source_name,
        )
        return error_envelope(cap, ctx["correlation_id"], ERR_VALIDATION,
                              "query is required and must be a non-empty string", audit)

    # Authorization is applied as a filter here (a search legitimately returns
    # "nothing you may see"), unlike a direct fetch where denial must be loud.
    visible = [
        c for c in ctx["adapter"].search_clients(query)
        if authz_mod.authorize_client_access(ctx["actor"], c, ctx["adapter"]).allowed
    ]
    matches = [
        {"client_id": c.client_id, "legal_name": c.legal_name,
         "jurisdiction": c.jurisdiction, "status": c.status,
         "risk_rating": c.risk_rating}
        for c in visible
    ]
    return _success(cap, ctx, {"query": query, "matches": matches,
                               "match_count": len(matches)})


def get_rm_client_context(payload: Dict) -> Dict:
    """Assemble the RM's working picture of one client.

    Composes CRM transactional data with the gate-verified ``client-lookup``
    skill (decision D3) — the skill stays the source of truth for client
    resolution and compliance flags.
    """
    cap = "get_rm_client_context"
    ctx, failure = _begin(cap, payload)
    if failure:
        return failure
    client, failure = _resolve_client(cap, ctx, payload.get("client_id"))
    if failure:
        return failure

    adapter = ctx["adapter"]

    # Wrap, do not re-implement: delegate to the gated skill.
    skill_result = SKILLS["client-lookup"]({
        "lookup_mode": "EXACT_ID",
        "client_id": client.client_id,
        "lookup_query": client.client_id,
    })
    skill_evidence = {
        "source_skill": "client-lookup",
        "match_type": skill_result.get("match_type"),
        "output_completeness": skill_result.get("output_completeness"),
        "audit_log_ref": skill_result.get("audit_log_ref"),
    }
    compliance_flags = skill_result.get("open_compliance_flags", []) or []

    opps = adapter.list_opportunities_for_client(client.client_id)
    open_opps = [_opp_brief(o) for o in opps if stage_is_open(o.stage)]
    tasks = adapter.list_tasks(client.client_id)
    open_tasks = [t for t in tasks if t.status == "OPEN"]

    missing: List[str] = []
    if not opps:
        missing.append("no opportunity on record for this client")
    if not adapter.list_activities(client.client_id):
        missing.append("no logged activity history")
    for o in opps:
        if stage_is_open(o.stage) and not o.amount:
            missing.append(f"{o.opportunity_id}: opportunity value not captured")
        if stage_is_open(o.stage) and o.service_type == "UNKNOWN":
            missing.append(f"{o.opportunity_id}: service type not qualified")

    result = {
        "client_id": client.client_id,
        "legal_name": client.legal_name,
        "jurisdiction": client.jurisdiction,
        "risk_rating": client.risk_rating,
        "status": client.status,
        "assigned_rm_id": client.assigned_rm_id,
        "open_opportunities": open_opps,
        "open_task_count": len(open_tasks),
        "compliance_flags": compliance_flags,
        "skill_evidence": skill_evidence,
        "missing_information": missing,
    }
    return _success(cap, ctx, result, client_id=client.client_id)


def get_opportunity_context(payload: Dict) -> Dict:
    """Assemble decision context for a single opportunity, including ageing."""
    cap = "get_opportunity_context"
    ctx, failure = _begin(cap, payload)
    if failure:
        return failure

    opportunity_id = payload.get("opportunity_id")
    if not opportunity_id or not isinstance(opportunity_id, str):
        audit = make_audit(
            capability=cap, correlation_id=ctx["correlation_id"],
            actor_type=ctx["actor"].actor_type, actor_id=ctx["actor"].actor_id,
            status="ERROR", authorization={"allowed": True, "reason": "actor recognised"},
            data_source=ctx["adapter"].source_name,
        )
        return error_envelope(cap, ctx["correlation_id"], ERR_VALIDATION,
                              "opportunity_id is required and must be a string", audit)

    opp = ctx["adapter"].get_opportunity(opportunity_id)
    if opp is None:
        audit = make_audit(
            capability=cap, correlation_id=ctx["correlation_id"],
            actor_type=ctx["actor"].actor_type, actor_id=ctx["actor"].actor_id,
            status="ERROR", authorization={"allowed": True, "reason": "actor recognised"},
            opportunity_id=opportunity_id, data_source=ctx["adapter"].source_name,
        )
        return error_envelope(cap, ctx["correlation_id"], ERR_OPPORTUNITY_NOT_FOUND,
                              f"No opportunity with id {opportunity_id!r}.", audit)

    # Authorization is decided against the owning client, not the opportunity.
    client, failure = _resolve_client(cap, ctx, opp.client_id)
    if failure:
        return failure

    activities = [_activity(a) for a in ctx["adapter"].list_activities(opp.client_id)
                  if a.opportunity_id == opp.opportunity_id]
    open_tasks = [_task(t) for t in ctx["adapter"].list_tasks(opp.client_id)
                  if t.opportunity_id == opp.opportunity_id and t.status == "OPEN"]

    missing: List[str] = []
    if not opp.amount:
        missing.append("opportunity value not captured")
    if opp.service_type == "UNKNOWN":
        missing.append("service type not qualified")
    if opp.expected_close_in_days is None:
        missing.append("expected close date not set")
    if not activities:
        missing.append("no activity logged against this opportunity")

    result = {
        "opportunity_id": opp.opportunity_id,
        "client_id": opp.client_id,
        "client_legal_name": client.legal_name,
        "name": opp.name,
        "stage": opp.stage,
        "amount": opp.amount,
        "currency": opp.currency,
        "service_type": opp.service_type,
        "expected_close_in_days": opp.expected_close_in_days,
        "aging": assess_aging(opp.stage, opp.days_in_stage),
        "recent_activity": activities,
        "open_tasks": open_tasks,
        "missing_information": missing,
    }
    return _success(cap, ctx, result, client_id=opp.client_id,
                    opportunity_id=opp.opportunity_id)


def get_client_history(payload: Dict) -> Dict:
    """Recent interaction history, most recent first."""
    cap = "get_client_history"
    ctx, failure = _begin(cap, payload)
    if failure:
        return failure
    client, failure = _resolve_client(cap, ctx, payload.get("client_id"))
    if failure:
        return failure

    acts = ctx["adapter"].list_activities(client.client_id)
    activities = [_activity(a) for a in acts]
    result = {
        "client_id": client.client_id,
        "activities": activities,
        "activity_count": len(activities),
        "days_since_last_activity": acts[0].occurred_days_ago if acts else None,
    }
    return _success(cap, ctx, result, client_id=client.client_id)


def get_open_tasks(payload: Dict) -> Dict:
    """Open tasks for a client, most overdue first."""
    cap = "get_open_tasks"
    ctx, failure = _begin(cap, payload)
    if failure:
        return failure
    client, failure = _resolve_client(cap, ctx, payload.get("client_id"))
    if failure:
        return failure

    tasks = [_task(t) for t in ctx["adapter"].list_tasks(client.client_id)
             if t.status == "OPEN"]
    result = {
        "client_id": client.client_id,
        "tasks": tasks,
        "open_count": len(tasks),
        "overdue_count": sum(1 for t in tasks if t["is_overdue"]),
    }
    return _success(cap, ctx, result, client_id=client.client_id)


def get_client_engagements(payload: Dict) -> Dict:
    """Service engagements held by the client."""
    cap = "get_client_engagements"
    ctx, failure = _begin(cap, payload)
    if failure:
        return failure
    client, failure = _resolve_client(cap, ctx, payload.get("client_id"))
    if failure:
        return failure

    engagements = [
        {"engagement_id": e.engagement_id, "service_type": e.service_type,
         "status": e.status, "renewal_in_days": e.renewal_in_days}
        for e in ctx["adapter"].list_engagements(client.client_id)
    ]
    result = {
        "client_id": client.client_id,
        "engagements": engagements,
        "active_count": sum(1 for e in engagements if e["status"] == "ACTIVE"),
    }
    return _success(cap, ctx, result, client_id=client.client_id)


def get_client_documents(payload: Dict) -> Dict:
    """Document status for the client, surfacing gaps explicitly."""
    cap = "get_client_documents"
    ctx, failure = _begin(cap, payload)
    if failure:
        return failure
    client, failure = _resolve_client(cap, ctx, payload.get("client_id"))
    if failure:
        return failure

    documents = [
        {"doc_id": d.doc_id, "doc_type": d.doc_type, "status": d.status,
         "days_until_expiry": d.days_until_expiry}
        for d in ctx["adapter"].list_documents(client.client_id)
    ]
    result = {
        "client_id": client.client_id,
        "documents": documents,
        "expired_count": sum(1 for d in documents if d["status"] == "EXPIRED"),
        "missing_count": sum(1 for d in documents if d["status"] == "MISSING"),
        "expiring_count": sum(1 for d in documents if d["status"] == "EXPIRING"),
    }
    return _success(cap, ctx, result, client_id=client.client_id)


def get_renewal_status(payload: Dict) -> Dict:
    """Upcoming renewals, soonest first.

    The urgency window is firm policy (config/thresholds.json), not a constant.
    """
    cap = "get_renewal_status"
    ctx, failure = _begin(cap, payload)
    if failure:
        return failure
    client, failure = _resolve_client(cap, ctx, payload.get("client_id"))
    if failure:
        return failure

    _urgent_window = _policy.load().urgent_renewal_days
    upcoming = [e for e in ctx["adapter"].list_engagements(client.client_id)
                if e.renewal_in_days is not None and e.status == "ACTIVE"]
    upcoming.sort(key=lambda e: e.renewal_in_days)
    renewals = [
        {"engagement_id": e.engagement_id, "service_type": e.service_type,
         "renewal_in_days": e.renewal_in_days,
         "is_urgent": e.renewal_in_days <= _urgent_window}
        for e in upcoming
    ]
    result = {
        "client_id": client.client_id,
        "renewals": renewals,
        "next_renewal_in_days": renewals[0]["renewal_in_days"] if renewals else None,
        "urgent_count": sum(1 for r in renewals if r["is_urgent"]),
    }
    return _success(cap, ctx, result, client_id=client.client_id)


CAPABILITIES: Dict[str, Callable[[Dict], Dict]] = {
    "search_client": search_client,
    "get_rm_client_context": get_rm_client_context,
    "get_opportunity_context": get_opportunity_context,
    "get_client_history": get_client_history,
    "get_open_tasks": get_open_tasks,
    "get_client_engagements": get_client_engagements,
    "get_client_documents": get_client_documents,
    "get_renewal_status": get_renewal_status,
}
