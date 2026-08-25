"""
Layer 4 — runtime output validation and the delivery gate.

Distinct from Layer 1 (regression eval, fixed fixtures, CI) and Layer 2 (tool
contract eval, build time). This layer validates **a live output, at the moment
it is about to reach a human**, and refuses delivery if anything is wrong.

It reuses ``capabilities.contracts.validate_envelope`` verbatim for structural
conformance — the shared-validator design from Phase 1/2 pays off here — and
adds the policy checks that only make sense at delivery time:

* **Grounding** — a workflow result must cite the capabilities it came from.
  An uncited recommendation is not auditable and is refused.
* **HITL enforcement** — anything carrying ``requires_human_review`` may not be
  delivered without a recorded ``APPROVED`` decision. This is the check that
  makes the flag real (§27: *flag ≠ enforced HITL*).
* **Non-repudiation** — an audit reference must be present.
* **No self-declared delivery** — an artefact may not claim it was sent; only
  the gate may change delivery status, and only after approval.

The gate fails **closed**: any violation blocks delivery.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from capabilities.contracts import validate_envelope
from hitl.approvals import STATE_APPROVED, ApprovalStore

# Values a result may legitimately carry before the gate runs.
_PRE_DELIVERY_STATUSES = ("DRAFT_NOT_SENT", "PENDING_DELIVERY")


def validate_runtime_output(envelope: Dict) -> Tuple[bool, List[str]]:
    """Structural + grounding validation of a live envelope.

    Does not consider approval state — see :func:`check_delivery` for that.
    """
    violations: List[str] = []

    structural_ok, structural = validate_envelope(envelope)
    violations.extend(structural)

    if not structural_ok:
        # Shape is already wrong; deeper policy checks would be noise.
        return False, violations

    if not envelope.get("ok"):
        # A well-formed error envelope is valid output; it is simply not
        # deliverable content.
        return True, []

    result = envelope.get("result") or {}
    audit = envelope.get("audit") or {}

    if not audit.get("audit_ref"):
        violations.append("audit.audit_ref is missing — output is not attributable")

    # Grounding: Tier 2 workflow results must cite their sources.
    if str(envelope.get("capability", "")).startswith("rm-"):
        if not result.get("sources"):
            violations.append(
                "result.sources is empty — an uncited recommendation is not auditable"
            )

    # An artefact may not declare itself delivered.
    status = result.get("delivery_status")
    if status is not None and status not in _PRE_DELIVERY_STATUSES:
        violations.append(
            f"delivery_status {status!r} claims delivery; only the delivery gate "
            "may set a delivered status, and only after approval"
        )

    return (len(violations) == 0), violations


def check_delivery(
    envelope: Dict,
    *,
    store: Optional[ApprovalStore] = None,
    approval_id: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """Decide whether this envelope may be delivered to a human recipient.

    Fails closed: an artefact requiring review is blocked unless ``store`` holds
    an ``APPROVED`` decision under ``approval_id``.
    """
    ok, violations = validate_runtime_output(envelope)
    if not ok:
        return False, violations

    if not envelope.get("ok"):
        return False, ["error envelopes are not deliverable content"]

    result = envelope.get("result") or {}

    if result.get("requires_human_review"):
        if store is None or approval_id is None:
            return False, [
                "requires_human_review is true but no approval record was supplied — "
                "delivery blocked pending human review"
            ]
        state = store.state_of(approval_id)
        if state is None:
            return False, [f"approval_id {approval_id!r} is not recorded"]
        if state != STATE_APPROVED:
            return False, [
                f"approval state is {state}; delivery requires {STATE_APPROVED}"
            ]

    return True, []


def deliver(
    envelope: Dict,
    *,
    store: Optional[ApprovalStore] = None,
    approval_id: Optional[str] = None,
) -> Dict:
    """Produce a delivery decision for an envelope.

    Returns a decision record rather than performing any transmission — v1
    exposes **no send capability at all** (Tier 3 is deferred). The decision is
    what a channel would consult before it transmitted anything.
    """
    allowed, violations = check_delivery(envelope, store=store, approval_id=approval_id)
    decision = {
        "delivered": allowed,
        "capability": envelope.get("capability"),
        "correlation_id": envelope.get("correlation_id"),
        "approval_id": approval_id,
        "approval_state": store.state_of(approval_id) if (store and approval_id) else None,
        "violations": violations,
        "delivery_status": "APPROVED_FOR_DELIVERY" if allowed else "BLOCKED",
    }
    return decision
