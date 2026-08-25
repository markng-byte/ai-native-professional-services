"""
Capability I/O contracts and the response envelope.

Implemented with the **standard library only**, deliberately. The protected
baseline (`src/skills`, `src/evals`, `run_evals.py`) is dependency-free and the
CI gate installs nothing; adding a runtime dependency such as pydantic to reach
the capability layer would compromise that hermetic property for no behavioural
gain at this phase. The declarative shape below is intentionally JSON-Schema-like
so it can be swapped for pydantic/JSON Schema at a transport boundary later
without changing any capability implementation.

Two consumers share one definition (which is why this module exists separately
from the tools):

* **Layer 2 — tool-contract eval** (build time, `tests/`): does every capability
  honour its declared schema, validation, authorization, errors, correlation id
  and audit reference?
* **Layer 4 — runtime validation** (later phase): is *this live envelope*
  well-formed before it is delivered to an RM?
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from capabilities.errors import ALL_ERROR_CODES

# ---------------------------------------------------------------------------
# Envelope construction
# ---------------------------------------------------------------------------

def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_audit(
    *,
    capability: str,
    correlation_id: str,
    actor_type: Optional[str],
    actor_id: Optional[str],
    status: str,
    authorization: Optional[Dict] = None,
    client_id: Optional[str] = None,
    opportunity_id: Optional[str] = None,
    data_source: str = "fixtures",
) -> Dict:
    """Build an audit record.

    Field selection follows `governance/GOVERNANCE.md` §5.1 (Tool API call /
    skill execution). Deliberately records *identifiers and outcomes only* — no
    payload bodies, no PII — per master prompt §22.
    """
    return {
        "audit_ref": str(uuid.uuid4()),
        "correlation_id": correlation_id,
        "capability": capability,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "client_id": client_id,
        "opportunity_id": opportunity_id,
        "authorization": authorization or {},
        "data_source": data_source,
        "status": status,
        "timestamp": _timestamp(),
    }


def ok_envelope(capability: str, correlation_id: str, result: Dict, audit: Dict) -> Dict:
    return {
        "ok": True,
        "capability": capability,
        "correlation_id": correlation_id,
        "result": result,
        "error": None,
        "audit": audit,
    }


def error_envelope(
    capability: str, correlation_id: str, code: str, message: str, audit: Dict
) -> Dict:
    return {
        "ok": False,
        "capability": capability,
        "correlation_id": correlation_id,
        "result": None,
        "error": {"code": code, "message": message},
        "audit": audit,
    }


def new_correlation_id(payload: Dict) -> str:
    """Honour a caller-supplied correlation id, else mint one."""
    supplied = payload.get("correlation_id")
    if isinstance(supplied, str) and supplied.strip():
        return supplied.strip()
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Declarative result contracts
# ---------------------------------------------------------------------------
# type tokens: "str" | "int" | "float" | "bool" | "list" | "dict" | "any"
# A trailing "?" marks the field nullable (present, but may be None).

_TYPES = {
    "str": str,
    "int": int,
    "float": (int, float),
    "bool": bool,
    "list": list,
    "dict": dict,
}

RESULT_CONTRACTS: Dict[str, Dict[str, str]] = {
    "search_client": {"query": "str", "matches": "list", "match_count": "int"},
    "get_rm_client_context": {
        "client_id": "str", "legal_name": "str", "jurisdiction": "str",
        "risk_rating": "str", "status": "str", "assigned_rm_id": "str",
        "open_opportunities": "list", "open_task_count": "int",
        "compliance_flags": "list", "skill_evidence": "dict",
        "missing_information": "list",
    },
    "get_opportunity_context": {
        "opportunity_id": "str", "client_id": "str", "name": "str", "stage": "str",
        "amount": "float", "currency": "str", "service_type": "str",
        "aging": "dict", "recent_activity": "list", "open_tasks": "list",
        "missing_information": "list",
    },
    "get_client_history": {"client_id": "str", "activities": "list", "activity_count": "int",
                           "days_since_last_activity": "int?"},
    "get_open_tasks": {"client_id": "str", "tasks": "list", "open_count": "int",
                       "overdue_count": "int"},
    "get_client_engagements": {"client_id": "str", "engagements": "list",
                               "active_count": "int"},
    "get_client_documents": {"client_id": "str", "documents": "list",
                             "expired_count": "int", "missing_count": "int",
                             "expiring_count": "int"},
    "get_renewal_status": {"client_id": "str", "renewals": "list",
                           "next_renewal_in_days": "int?", "urgent_count": "int"},
}


def register_contracts(mapping: Dict[str, Dict[str, str]]) -> None:
    """Register result contracts for a higher tier (e.g. Tier 2 RM workflows).

    Keeps a *single* ``validate_envelope`` implementation shared by the Layer 2
    contract eval and the future Layer 4 runtime validator, rather than forking
    a second validator per tier. Registration is explicit (called from
    :mod:`rm`), not implicit, so the contract set is always traceable.
    """
    overlap = set(mapping) & set(RESULT_CONTRACTS)
    if overlap:
        raise ValueError(f"contract names already registered: {sorted(overlap)}")
    RESULT_CONTRACTS.update(mapping)

# Fields every envelope must carry, regardless of capability.
_ENVELOPE_FIELDS = ("ok", "capability", "correlation_id", "result", "error", "audit")
_AUDIT_FIELDS = (
    "audit_ref", "correlation_id", "capability", "actor_type", "actor_id",
    "authorization", "data_source", "status", "timestamp",
)


def _check_field(value, spec: str) -> Optional[str]:
    nullable = spec.endswith("?")
    token = spec[:-1] if nullable else spec
    if value is None:
        return None if nullable else "is None but not declared nullable"
    if token == "any":
        return None
    expected = _TYPES.get(token)
    if expected is None:
        return f"unknown type token {token!r}"
    if isinstance(value, bool) and expected is not bool:
        return f"expected {token}, got bool"
    if not isinstance(value, expected):
        return f"expected {token}, got {type(value).__name__}"
    return None


def validate_envelope(envelope: Dict) -> Tuple[bool, List[str]]:
    """Validate an envelope against the shared contract.

    Used by the Layer-2 contract eval now and reusable verbatim as the Layer-4
    runtime validator later.
    """
    violations: List[str] = []

    if not isinstance(envelope, dict):
        return False, ["envelope is not a dict"]

    for f in _ENVELOPE_FIELDS:
        if f not in envelope:
            violations.append(f"envelope missing field {f!r}")
    if violations:
        return False, violations

    capability = envelope.get("capability")
    if not isinstance(capability, str) or not capability:
        violations.append("capability must be a non-empty string")

    if not isinstance(envelope.get("correlation_id"), str) or not envelope["correlation_id"]:
        violations.append("correlation_id must be a non-empty string")

    # audit is mandatory on success and failure alike
    audit = envelope.get("audit")
    if not isinstance(audit, dict):
        violations.append("audit must be a dict")
    else:
        for f in _AUDIT_FIELDS:
            if f not in audit:
                violations.append(f"audit missing field {f!r}")
        if audit.get("correlation_id") != envelope.get("correlation_id"):
            violations.append("audit.correlation_id does not match envelope.correlation_id")

    ok = envelope.get("ok")
    if not isinstance(ok, bool):
        violations.append("ok must be a bool")
        return False, violations

    if ok:
        if envelope.get("error") is not None:
            violations.append("ok=True but error is not None")
        result = envelope.get("result")
        if not isinstance(result, dict):
            violations.append("ok=True but result is not a dict")
        else:
            contract = RESULT_CONTRACTS.get(capability)
            if contract is None:
                violations.append(f"no result contract declared for {capability!r}")
            else:
                for fname, spec in contract.items():
                    if fname not in result:
                        violations.append(f"result missing field {fname!r}")
                        continue
                    problem = _check_field(result[fname], spec)
                    if problem:
                        violations.append(f"result.{fname} {problem}")
    else:
        if envelope.get("result") is not None:
            violations.append("ok=False but result is not None")
        err = envelope.get("error")
        if not isinstance(err, dict):
            violations.append("ok=False but error is not a dict")
        else:
            if err.get("code") not in ALL_ERROR_CODES:
                violations.append(f"error.code {err.get('code')!r} is not a registered code")
            if not isinstance(err.get("message"), str) or not err["message"]:
                violations.append("error.message must be a non-empty string")

    return (len(violations) == 0), violations
