"""
Human-in-the-loop approval store and state machine.

This module is what turns ``requires_human_review`` from a **returned flag**
into an **enforced stop**. Master prompt §27 is explicit that a flag is not
HITL; until Phase 3 the RM Co-pilot only *reported* that review was needed and
nothing prevented delivery.

State machine
-------------
::

    DRAFTED ──submit──► PENDING_REVIEW ──approve──► APPROVED   (terminal)
                                       └─reject───► REJECTED   (terminal)

Illegal transitions are refused, not coerced. Terminal states never change: an
approved artefact cannot be silently re-approved, and a rejected one cannot be
resurrected — a new draft must be submitted instead.

Approver policy
---------------
Roles come from the approval matrix in ``governance/GOVERNANCE.md`` §2. The
matrix already names the **Relationship Manager** as approver for engagement
letter sends (row 4), banking introduction sends (row 5) and client-facing
research (row 7), and reserves compliance outcomes for the **Compliance
Officer** (rows 1–2). That mapping is encoded in :data:`ACTION_POLICIES` rather
than reinvented, so a compliance-triggered draft cannot be waved through by the
RM who wrote it.

Persistence
-----------
v1 uses an in-process store with an append-only event log. The interface is
deliberately storage-shaped (``submit`` / ``get`` / ``decide`` / ``events``) so
a durable backend can replace it without touching callers. Records are never
mutated in place — each transition appends an event and rewrites the record's
state, preserving the trail required by ``GOVERNANCE.md`` §5.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from hitl.storage import (
    ApprovalStorage,
    ApprovalStorageError,
    InMemoryApprovalStorage,
    default_storage,
)

# --- states ---------------------------------------------------------------

STATE_DRAFTED = "DRAFTED"
STATE_PENDING_REVIEW = "PENDING_REVIEW"
STATE_APPROVED = "APPROVED"
STATE_REJECTED = "REJECTED"

TERMINAL_STATES = (STATE_APPROVED, STATE_REJECTED)

_ALLOWED_TRANSITIONS = {
    STATE_DRAFTED: (STATE_PENDING_REVIEW,),
    STATE_PENDING_REVIEW: (STATE_APPROVED, STATE_REJECTED),
    STATE_APPROVED: (),
    STATE_REJECTED: (),
}

# --- roles ----------------------------------------------------------------

ROLE_RM = "RELATIONSHIP_MANAGER"
ROLE_COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"
ROLE_DEPARTMENT_HEAD = "DEPARTMENT_HEAD"


@dataclass(frozen=True)
class ActionPolicy:
    action_type: str
    risk_level: str
    auto_approved: bool
    required_role: str
    override_allowed: bool
    override_role: Optional[str]
    governance_ref: str


# Mirrors governance/GOVERNANCE.md §2. Only the rows reachable from RM
# Co-pilot v1 are encoded; Tier 3 execution actions are absent by design.
ACTION_POLICIES: Dict[str, ActionPolicy] = {
    "rm_followup_send": ActionPolicy(
        "rm_followup_send", "MEDIUM-HIGH", False, ROLE_RM, True,
        ROLE_DEPARTMENT_HEAD, "GOVERNANCE.md §2 row 4 (agent drafts; human reviews and sends)",
    ),
    "engagement_letter_send": ActionPolicy(
        "engagement_letter_send", "MEDIUM-HIGH", False, ROLE_RM, True,
        ROLE_DEPARTMENT_HEAD, "GOVERNANCE.md §2 row 4",
    ),
    "banking_intro_send": ActionPolicy(
        "banking_intro_send", "MEDIUM-HIGH", False, ROLE_RM, True,
        ROLE_DEPARTMENT_HEAD, "GOVERNANCE.md §2 row 5",
    ),
    "research_output_share": ActionPolicy(
        "research_output_share", "MEDIUM", False, ROLE_RM, True,
        ROLE_DEPARTMENT_HEAD, "GOVERNANCE.md §2 row 7",
    ),
    # Compliance outcomes are reserved to the Compliance Officer and cannot be
    # overridden — GOVERNANCE.md §2 rows 1-2.
    "compliance_escalation": ActionPolicy(
        "compliance_escalation", "CRITICAL", False, ROLE_COMPLIANCE_OFFICER, False,
        None, "GOVERNANCE.md §2 rows 1-2 (match = block; must escalate)",
    ),
}

DEFAULT_ACTION_TYPE = "rm_followup_send"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ApprovalRecord:
    approval_id: str
    action_type: str
    state: str
    correlation_id: Optional[str]
    capability: Optional[str]
    client_id: Optional[str]
    submitted_by: Optional[str]
    required_role: str
    payload_ref: Dict                      # identifiers only — never the body
    events: List[Dict] = field(default_factory=list)
    decided_by: Optional[str] = None
    decision_justification: Optional[str] = None

    def as_dict(self) -> Dict:
        return {
            "approval_id": self.approval_id,
            "action_type": self.action_type,
            "state": self.state,
            "correlation_id": self.correlation_id,
            "capability": self.capability,
            "client_id": self.client_id,
            "submitted_by": self.submitted_by,
            "required_role": self.required_role,
            "payload_ref": dict(self.payload_ref),
            "decided_by": self.decided_by,
            "decision_justification": self.decision_justification,
            "events": [dict(e) for e in self.events],
        }


class ApprovalError(Exception):
    """Raised on an illegal transition or an unauthorized approver."""


class ApprovalStore:
    """Approval store with an append-only event trail.

    Business rules (legal transitions, approver roles, mandatory justification)
    live here; persistence lives in :mod:`hitl.storage`. The public interface is
    unchanged from the in-memory version, so callers need no modification when a
    durable backend is used.

    ``storage`` defaults to :func:`hitl.storage.default_storage`, which selects
    SQLite when ``FIRMOS_APPROVAL_DB`` is set and stays in-memory otherwise.
    """

    def __init__(self, storage: Optional[ApprovalStorage] = None) -> None:
        self._storage: ApprovalStorage = storage or default_storage()

    @property
    def backend(self) -> str:
        return getattr(self._storage, "backend_name", "unknown")

    @property
    def durable(self) -> bool:
        """Whether approvals survive a restart. Surfaced so a UI can say so."""
        return bool(getattr(self._storage, "durable", False))

    @staticmethod
    def _to_record(data: Dict) -> "ApprovalRecord":
        record = ApprovalRecord(
            approval_id=data["approval_id"],
            action_type=data["action_type"],
            state=data["state"],
            correlation_id=data.get("correlation_id"),
            capability=data.get("capability"),
            client_id=data.get("client_id"),
            submitted_by=data.get("submitted_by"),
            required_role=data["required_role"],
            payload_ref=dict(data.get("payload_ref") or {}),
            events=[dict(e) for e in data.get("events") or []],
            decided_by=data.get("decided_by"),
            decision_justification=data.get("decision_justification"),
        )
        return record

    # -- submission --------------------------------------------------------

    def submit(self, envelope: Dict, *, action_type: str = DEFAULT_ACTION_TYPE,
               submitted_by: Optional[str] = None) -> ApprovalRecord:
        """Move an artefact from DRAFTED into PENDING_REVIEW."""
        policy = ACTION_POLICIES.get(action_type)
        if policy is None:
            raise ApprovalError(f"Unknown action_type {action_type!r}.")

        result = envelope.get("result") or {}
        current = result.get("approval_state", STATE_DRAFTED)
        if STATE_PENDING_REVIEW not in _ALLOWED_TRANSITIONS.get(current, ()):
            raise ApprovalError(
                f"Cannot submit for review from state {current!r}; "
                f"only {STATE_DRAFTED} may be submitted."
            )

        audit = envelope.get("audit") or {}
        record = ApprovalRecord(
            approval_id=str(uuid.uuid4()),
            action_type=action_type,
            state=STATE_PENDING_REVIEW,
            correlation_id=envelope.get("correlation_id"),
            capability=envelope.get("capability"),
            client_id=audit.get("client_id") or result.get("client_id"),
            submitted_by=submitted_by or audit.get("actor_id"),
            required_role=policy.required_role,
            # Identifiers only: the drafted body is not copied into the
            # governance record (§22 — do not log unnecessary sensitive data).
            payload_ref={
                "audit_ref": audit.get("audit_ref"),
                "based_on_signal": result.get("based_on_signal"),
                "governance_ref": policy.governance_ref,
            },
        )
        event = {
            "event": "SUBMITTED", "from": current, "to": STATE_PENDING_REVIEW,
            "actor": record.submitted_by, "timestamp": _now(),
        }
        record.events.append(event)
        self._storage.insert(record.as_dict(), event)
        return record

    # -- decision ----------------------------------------------------------

    def decide(self, approval_id: str, *, decision: str, reviewer_id: str,
               reviewer_role: str, justification: Optional[str] = None) -> ApprovalRecord:
        """Approve or reject a pending artefact."""
        data = self._storage.get(approval_id)
        if data is None:
            raise ApprovalError(f"Unknown approval_id {approval_id!r}.")
        record = self._to_record(data)

        if decision not in (STATE_APPROVED, STATE_REJECTED):
            raise ApprovalError(
                f"decision must be {STATE_APPROVED} or {STATE_REJECTED}, got {decision!r}."
            )

        if decision not in _ALLOWED_TRANSITIONS.get(record.state, ()):
            raise ApprovalError(
                f"Illegal transition {record.state} -> {decision}. "
                f"State {record.state} is terminal or does not permit this decision."
            )

        if reviewer_role != record.required_role:
            raise ApprovalError(
                f"Role {reviewer_role!r} may not decide {record.action_type!r}; "
                f"{record.required_role!r} is required "
                f"({ACTION_POLICIES[record.action_type].governance_ref})."
            )

        if decision == STATE_REJECTED and not justification:
            raise ApprovalError("A rejection requires a justification.")

        event = {
            "event": decision, "from": record.state, "to": decision,
            "actor": reviewer_id, "role": reviewer_role,
            "justification": justification, "timestamp": _now(),
        }
        try:
            # Compare-and-set against the state we just validated. If another
            # reviewer decided this item first, the storage layer refuses rather
            # than letting one decision silently overwrite the other.
            updated = self._storage.transition(
                approval_id,
                expected_state=record.state,
                new_state=decision,
                event=event,
                decided_by=reviewer_id,
                justification=justification,
            )
        except ApprovalStorageError as exc:
            raise ApprovalError(str(exc)) from exc

        return self._to_record(updated)

    # -- reads -------------------------------------------------------------

    def get(self, approval_id: str) -> Optional[ApprovalRecord]:
        data = self._storage.get(approval_id)
        return self._to_record(data) if data else None

    def state_of(self, approval_id: str) -> Optional[str]:
        data = self._storage.get(approval_id)
        return data["state"] if data else None

    def pending(self) -> List[ApprovalRecord]:
        return [self._to_record(d)
                for d in self._storage.list_by_state(STATE_PENDING_REVIEW)]


def action_type_for(envelope: Dict) -> str:
    """Choose the governance policy that applies to a drafted artefact.

    A draft produced because of an open compliance flag is a compliance
    outcome, not routine correspondence — it escalates to the Compliance
    Officer (GOVERNANCE.md §2 rows 1-2) rather than being approvable by the RM
    who requested it.
    """
    result = envelope.get("result") or {}
    if result.get("based_on_signal") in ("COMPLIANCE_FLAG_OPEN", "DOCUMENT_EXPIRED"):
        return "compliance_escalation"
    return DEFAULT_ACTION_TYPE
