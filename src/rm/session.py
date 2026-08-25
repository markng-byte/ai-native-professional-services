"""
RM working session — the controller behind the surface.

Holds what the RM is currently working on and routes every request through the
governed stack. **No Streamlit import**, so the whole control flow is testable
headlessly.

    RMSession -> RM_WORKFLOWS -> CAPABILITIES -> CRMAdapter
              -> hitl.ApprovalStore
              -> validation.deliver

The surface calls this; it never calls a workflow, a capability or an adapter
directly. That keeps one composition path and prevents the view from acquiring
business logic of its own.

Session state is **working memory only** (decision D6): the selected RM, client
and opportunity, and the ids of drafts submitted for approval. Nothing about a
client is cached here — that would be the shadow CRM §7.3 forbids. Every read
goes back to the workflows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from hitl import ApprovalStore, action_type_for
from hitl.approvals import ApprovalRecord
from rm import RM_WORKFLOWS
from validation import deliver


@dataclass
class RMSession:
    """One RM's working context."""

    rm_id: Optional[str] = None
    client_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    store: ApprovalStore = field(default_factory=ApprovalStore)

    # The most recent draft envelope and the approval it was submitted under.
    draft_envelope: Optional[Dict] = None
    approval_id: Optional[str] = None

    # ---- actor -----------------------------------------------------------

    @property
    def actor(self) -> Dict:
        return {"rm_id": self.rm_id}

    def select_rm(self, rm_id: str) -> None:
        """Switch RM. Clears everything scoped to the previous actor.

        Not housekeeping — carrying a client selection across an actor switch
        would show one RM a client picked under another RM's authorization.
        """
        if rm_id != self.rm_id:
            self.client_id = None
            self.opportunity_id = None
            self.draft_envelope = None
            self.approval_id = None
        self.rm_id = rm_id

    def select_client(self, client_id: Optional[str]) -> None:
        if client_id != self.client_id:
            self.opportunity_id = None
            self.draft_envelope = None
            self.approval_id = None
        self.client_id = client_id

    def select_opportunity(self, opportunity_id: Optional[str]) -> None:
        self.opportunity_id = opportunity_id

    @property
    def is_ready(self) -> bool:
        return bool(self.rm_id and self.client_id)

    # ---- reads (always fresh; nothing cached) ----------------------------

    def _run(self, workflow: str, **params) -> Dict:
        return RM_WORKFLOWS[workflow]({"actor": self.actor, **params})

    def search(self, query: str) -> Dict:
        from capabilities import CAPABILITIES
        # The only direct capability call the surface makes: client discovery
        # has no Tier 2 workflow, so there is nothing to duplicate here.
        return CAPABILITIES["search_client"]({"actor": self.actor, "query": query})

    def client_summary(self) -> Dict:
        return self._run("rm-client-summary", client_id=self.client_id)

    def next_best_action(self) -> Dict:
        return self._run("rm-next-best-action", client_id=self.client_id)

    def opportunity_review(self, opportunity_id: Optional[str] = None) -> Dict:
        return self._run("rm-opportunity-review",
                         opportunity_id=opportunity_id or self.opportunity_id)

    # ---- draft -> approval -> gate ---------------------------------------

    def generate_draft(self) -> Dict:
        """Produce a follow-up draft and make it the session's current draft."""
        envelope = self._run("rm-followup-draft", client_id=self.client_id)
        self.draft_envelope = envelope
        self.approval_id = None          # a new draft is not the approved one
        return envelope

    def required_role(self) -> Optional[str]:
        """Which role must approve the current draft, per governance policy."""
        if not self.draft_envelope or not self.draft_envelope.get("ok"):
            return None
        from hitl.approvals import ACTION_POLICIES
        return ACTION_POLICIES[action_type_for(self.draft_envelope)].required_role

    def submit_for_review(self) -> ApprovalRecord:
        if not self.draft_envelope or not self.draft_envelope.get("ok"):
            raise ValueError("There is no valid draft to submit.")
        record = self.store.submit(
            self.draft_envelope,
            action_type=action_type_for(self.draft_envelope),
            submitted_by=self.rm_id,
        )
        self.approval_id = record.approval_id
        return record

    def decide(self, decision: str, *, reviewer_id: str, reviewer_role: str,
               justification: Optional[str] = None) -> ApprovalRecord:
        if not self.approval_id:
            raise ValueError("Nothing has been submitted for review.")
        return self.store.decide(
            self.approval_id, decision=decision, reviewer_id=reviewer_id,
            reviewer_role=reviewer_role, justification=justification,
        )

    def approval_record(self) -> Optional[Dict]:
        if not self.approval_id:
            return None
        record = self.store.get(self.approval_id)
        return record.as_dict() if record else None

    def delivery_decision(self) -> Optional[Dict]:
        """Ask the gate whether the current draft may be delivered."""
        if not self.draft_envelope:
            return None
        return deliver(self.draft_envelope, store=self.store,
                       approval_id=self.approval_id)

    def pending_approvals(self) -> List[Dict]:
        return [r.as_dict() for r in self.store.pending()]

    # ---- storage transparency --------------------------------------------

    def storage_notice(self) -> Dict:
        """Whether approvals will survive a restart, in words a reviewer can act on.

        A reviewer is being asked to make a governance decision that
        ``GOVERNANCE.md`` §5.1 says must be retained for seven years. If the
        store is in-memory, that decision disappears when the process stops —
        so the surface says so rather than letting the reviewer assume
        otherwise.
        """
        durable = self.store.durable
        return {
            "durable": durable,
            "backend": self.store.backend,
            "message": (
                f"Approvals are recorded durably ({self.store.backend})."
                if durable else
                "⚠️ Approvals are held in memory and will be lost when this "
                "process restarts. Set FIRMOS_APPROVAL_DB to retain them as "
                "audit records."
            ),
        }
