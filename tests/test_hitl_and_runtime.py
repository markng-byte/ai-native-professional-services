"""
Phase 3 tests — HITL enforcement, Layer 4 runtime validation, and the removal
of duplicated business logic.

Three concerns, deliberately kept in one suite because they share the same
thesis: *what the system claims must be what the system does.*

  * HITL: ``requires_human_review`` is enforced, not merely reported.
  * Layer 4: live outputs are validated before they can reach a human.
  * Single source of truth: the UI and the agent runtime must agree with the
    gated skills, not carry their own copies.
"""

from __future__ import annotations

import ast
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from hitl import (                                    # noqa: E402
    ACTION_POLICIES,
    STATE_APPROVED,
    STATE_PENDING_REVIEW,
    STATE_REJECTED,
    ApprovalError,
    ApprovalStore,
    action_type_for,
)
from hitl.approvals import ROLE_COMPLIANCE_OFFICER, ROLE_RM   # noqa: E402
from rm import RM_WORKFLOWS                           # noqa: E402
from validation import check_delivery, deliver, validate_runtime_output  # noqa: E402

RM = {"rm_id": "RM-001"}
RM_DAVID = {"rm_id": "RM-002"}
OWNED_CLIENT = "CLT-001234"


def draft(client_id=OWNED_CLIENT, actor=RM):
    return RM_WORKFLOWS["rm-followup-draft"]({"actor": actor, "client_id": client_id})


class TestApprovalStateMachine(unittest.TestCase):
    def setUp(self):
        self.store = ApprovalStore()

    def test_submit_moves_to_pending_review(self):
        rec = self.store.submit(draft(), submitted_by="RM-001")
        self.assertEqual(rec.state, STATE_PENDING_REVIEW)
        self.assertEqual(rec.events[0]["event"], "SUBMITTED")

    def test_approve_transitions_and_records_actor(self):
        rec = self.store.submit(draft(), submitted_by="RM-001")
        out = self.store.decide(rec.approval_id, decision=STATE_APPROVED,
                                reviewer_id="RM-001", reviewer_role=ROLE_RM)
        self.assertEqual(out.state, STATE_APPROVED)
        self.assertEqual(out.decided_by, "RM-001")

    def test_reject_requires_justification(self):
        rec = self.store.submit(draft(), submitted_by="RM-001")
        with self.assertRaises(ApprovalError):
            self.store.decide(rec.approval_id, decision=STATE_REJECTED,
                              reviewer_id="RM-001", reviewer_role=ROLE_RM)
        out = self.store.decide(rec.approval_id, decision=STATE_REJECTED,
                                reviewer_id="RM-001", reviewer_role=ROLE_RM,
                                justification="Tone unsuitable for this client.")
        self.assertEqual(out.state, STATE_REJECTED)

    def test_terminal_states_are_final(self):
        for decision, kwargs in (
            (STATE_APPROVED, {}),
            (STATE_REJECTED, {"justification": "not appropriate"}),
        ):
            with self.subTest(decision=decision):
                store = ApprovalStore()
                rec = store.submit(draft(), submitted_by="RM-001")
                store.decide(rec.approval_id, decision=decision,
                             reviewer_id="RM-001", reviewer_role=ROLE_RM, **kwargs)
                with self.assertRaises(ApprovalError):
                    store.decide(rec.approval_id, decision=STATE_APPROVED,
                                 reviewer_id="RM-001", reviewer_role=ROLE_RM)

    def test_cannot_submit_twice(self):
        env = draft()
        self.store.submit(env, submitted_by="RM-001")
        # The envelope is still DRAFTED, but a second submission creates a
        # second record; what must not happen is submitting an already-decided
        # artefact. Simulate by mutating the result state.
        env["result"]["approval_state"] = STATE_APPROVED
        with self.assertRaises(ApprovalError):
            self.store.submit(env, submitted_by="RM-001")

    def test_unknown_approval_id_rejected(self):
        with self.assertRaises(ApprovalError):
            self.store.decide("nope", decision=STATE_APPROVED,
                              reviewer_id="RM-001", reviewer_role=ROLE_RM)

    def test_event_trail_is_append_only(self):
        rec = self.store.submit(draft(), submitted_by="RM-001")
        decided = self.store.decide(rec.approval_id, decision=STATE_APPROVED,
                                    reviewer_id="RM-001", reviewer_role=ROLE_RM)
        events = [e["event"] for e in decided.events]
        self.assertEqual(events, ["SUBMITTED", STATE_APPROVED])
        # Re-reading gives the same trail — the record is not a live handle.
        self.assertEqual([e["event"] for e in self.store.get(rec.approval_id).events],
                         ["SUBMITTED", STATE_APPROVED])

    def test_returned_records_are_snapshots_not_live_handles(self):
        """A record read before a decision must not mutate underneath the caller.

        The in-memory store previously handed back the live object, so an old
        reference silently gained new events. With durable storage a record is a
        point-in-time snapshot; callers re-read to see changes. Pinned here so
        the semantics are deliberate rather than incidental.
        """
        stale = self.store.submit(draft(), submitted_by="RM-001")
        self.store.decide(stale.approval_id, decision=STATE_APPROVED,
                          reviewer_id="RM-001", reviewer_role=ROLE_RM)
        self.assertEqual(stale.state, STATE_PENDING_REVIEW)
        self.assertEqual(self.store.state_of(stale.approval_id), STATE_APPROVED)

    def test_governance_record_holds_no_document_body(self):
        """§22 — identifiers only; the drafted text is not copied into governance."""
        rec = self.store.submit(draft(), submitted_by="RM-001")
        serialized = str(rec.as_dict())
        self.assertNotIn("Dear [CONTACT NAME]", serialized)
        self.assertIn("governance_ref", rec.payload_ref)


class TestApproverPolicy(unittest.TestCase):
    """Roles come from the governance approval matrix, not from the caller."""

    def setUp(self):
        self.store = ApprovalStore()

    def test_wrong_role_cannot_approve(self):
        rec = self.store.submit(draft(), submitted_by="RM-001")
        with self.assertRaises(ApprovalError):
            self.store.decide(rec.approval_id, decision=STATE_APPROVED,
                              reviewer_id="X", reviewer_role=ROLE_COMPLIANCE_OFFICER)

    def test_compliance_draft_escalates_beyond_the_rm(self):
        """A compliance-triggered draft may not be waved through by the RM."""
        env = draft(client_id="CLT-009001", actor=RM_DAVID)
        self.assertEqual(env["result"]["based_on_signal"], "COMPLIANCE_FLAG_OPEN")

        action_type = action_type_for(env)
        self.assertEqual(action_type, "compliance_escalation")

        rec = self.store.submit(env, action_type=action_type, submitted_by="RM-002")
        with self.assertRaises(ApprovalError):
            self.store.decide(rec.approval_id, decision=STATE_APPROVED,
                              reviewer_id="RM-002", reviewer_role=ROLE_RM)
        out = self.store.decide(rec.approval_id, decision=STATE_APPROVED,
                                reviewer_id="CO-1", reviewer_role=ROLE_COMPLIANCE_OFFICER)
        self.assertEqual(out.state, STATE_APPROVED)

    def test_compliance_escalation_is_not_overridable(self):
        policy = ACTION_POLICIES["compliance_escalation"]
        self.assertFalse(policy.override_allowed)
        self.assertFalse(policy.auto_approved)

    def test_no_policy_is_auto_approved(self):
        for name, policy in ACTION_POLICIES.items():
            with self.subTest(action=name):
                self.assertFalse(policy.auto_approved)


class TestRuntimeValidation(unittest.TestCase):
    def test_valid_workflow_output_passes(self):
        for wf, params in [
            ("rm-client-summary", {"client_id": OWNED_CLIENT}),
            ("rm-next-best-action", {"client_id": OWNED_CLIENT}),
            ("rm-opportunity-review", {"opportunity_id": "OPP-1002"}),
            ("rm-followup-draft", {"client_id": OWNED_CLIENT}),
        ]:
            with self.subTest(workflow=wf):
                env = RM_WORKFLOWS[wf]({"actor": RM, **params})
                ok, violations = validate_runtime_output(env)
                self.assertTrue(ok, violations)

    def test_uncited_recommendation_is_refused(self):
        env = RM_WORKFLOWS["rm-next-best-action"]({"actor": RM, "client_id": OWNED_CLIENT})
        env["result"]["sources"] = []
        ok, violations = validate_runtime_output(env)
        self.assertFalse(ok)
        self.assertTrue(any("uncited" in v for v in violations))

    def test_missing_audit_ref_is_refused(self):
        env = draft()
        env["audit"]["audit_ref"] = None
        ok, violations = validate_runtime_output(env)
        self.assertFalse(ok)
        self.assertTrue(any("audit_ref" in v for v in violations))

    def test_self_declared_delivery_is_refused(self):
        env = draft()
        env["result"]["delivery_status"] = "SENT"
        ok, violations = validate_runtime_output(env)
        self.assertFalse(ok)
        self.assertTrue(any("claims delivery" in v for v in violations))

    def test_malformed_envelope_is_refused(self):
        ok, violations = validate_runtime_output({"ok": True})
        self.assertFalse(ok)
        self.assertTrue(violations)


class TestDeliveryGate(unittest.TestCase):
    """The check that makes requires_human_review real."""

    def setUp(self):
        self.store = ApprovalStore()

    def test_draft_cannot_be_delivered_without_approval(self):
        env = draft()
        allowed, violations = check_delivery(env)
        self.assertFalse(allowed)
        self.assertTrue(any("delivery blocked" in v for v in violations))

    def test_draft_cannot_be_delivered_while_pending(self):
        env = draft()
        rec = self.store.submit(env, submitted_by="RM-001")
        allowed, violations = check_delivery(env, store=self.store,
                                             approval_id=rec.approval_id)
        self.assertFalse(allowed)
        self.assertTrue(any(STATE_PENDING_REVIEW in v for v in violations))

    def test_draft_delivers_only_after_approval(self):
        env = draft()
        rec = self.store.submit(env, submitted_by="RM-001")
        self.store.decide(rec.approval_id, decision=STATE_APPROVED,
                          reviewer_id="RM-001", reviewer_role=ROLE_RM)
        allowed, violations = check_delivery(env, store=self.store,
                                             approval_id=rec.approval_id)
        self.assertTrue(allowed, violations)

    def test_rejected_draft_never_delivers(self):
        env = draft()
        rec = self.store.submit(env, submitted_by="RM-001")
        self.store.decide(rec.approval_id, decision=STATE_REJECTED,
                          reviewer_id="RM-001", reviewer_role=ROLE_RM,
                          justification="Not appropriate.")
        allowed, _ = check_delivery(env, store=self.store, approval_id=rec.approval_id)
        self.assertFalse(allowed)

    def test_unknown_approval_id_blocks(self):
        env = draft()
        allowed, violations = check_delivery(env, store=self.store, approval_id="ghost")
        self.assertFalse(allowed)
        self.assertTrue(any("not recorded" in v for v in violations))

    def test_error_envelope_is_not_deliverable(self):
        env = RM_WORKFLOWS["rm-client-summary"]({"actor": RM, "client_id": "CLT-005567"})
        self.assertFalse(env["ok"])
        allowed, _ = check_delivery(env)
        self.assertFalse(allowed)

    def test_gate_fails_closed_on_any_violation(self):
        env = draft()
        rec = self.store.submit(env, submitted_by="RM-001")
        self.store.decide(rec.approval_id, decision=STATE_APPROVED,
                          reviewer_id="RM-001", reviewer_role=ROLE_RM)
        env["result"]["sources"] = []          # approved, but now ungrounded
        allowed, violations = check_delivery(env, store=self.store,
                                             approval_id=rec.approval_id)
        self.assertFalse(allowed, "approval must not excuse a contract violation")

    def test_deliver_returns_a_decision_not_a_transmission(self):
        env = draft()
        decision = deliver(env)
        self.assertFalse(decision["delivered"])
        self.assertEqual(decision["delivery_status"], "BLOCKED")
        self.assertIn("violations", decision)

    def test_non_review_output_delivers_freely(self):
        """A summary carries no requires_human_review and needs no approval."""
        env = RM_WORKFLOWS["rm-client-summary"]({"actor": RM, "client_id": OWNED_CLIENT})
        allowed, violations = check_delivery(env)
        self.assertTrue(allowed, violations)


class TestSingleSourceOfTruth(unittest.TestCase):
    """R1-R3: the UI and agent runtime must not carry their own copies."""

    def test_engine_classification_agrees_with_the_gated_skill(self):
        import engine
        from skills import SKILLS
        prompts = [
            "Compare BVI and Cayman for a holding company",
            "Run a sanctions screen on John Doe",
            "Draft an engagement letter for Acme",
            "Which mandates are expiring in the next 90 days?",
            "Who is the ultimate beneficial owner of Global Ventures Ltd?",
            "Can you help me with my company?",
            "nead a engagment leter for my client XYZ",
        ]
        for p in prompts:
            with self.subTest(prompt=p):
                skill = SKILLS["intent-classifier"]({"raw_message": p})
                ui = engine.classify(p)
                self.assertEqual(ui.label, skill["intent_label"])
                self.assertEqual(ui.route, skill["routing_target"])
                self.assertEqual(ui.confidence, skill["confidence_score"])

    def test_engine_jurisdiction_data_is_derived_from_the_skill(self):
        import engine
        from skills.jurisdiction_compare import _CORPUS
        for code, row in _CORPUS.items():
            with self.subTest(code=code):
                self.assertEqual(engine._JURIS_DATA[code]["cost"], row["cost"])
                self.assertEqual(engine._JURIS_DATA[code]["tax"], row["tax"])
                self.assertEqual(engine._JURIS_DATA[code]["banking"], row["banking"])

    def test_engine_public_surface_is_unchanged(self):
        """app.py depends on these names; the refactor must not move them."""
        import engine
        for name in ("AGENTS", "USE_CASES", "STATUS_IDLE", "STATUS_QUEUED",
                     "STATUS_THINKING", "STATUS_WORKING", "STATUS_DONE",
                     "STATUS_BLOCKED", "classify", "build_pipeline", "now_ts",
                     "Stage", "Intent"):
            with self.subTest(name=name):
                self.assertTrue(hasattr(engine, name), f"engine.{name} disappeared")

    def test_engine_pipeline_still_builds_for_every_use_case(self):
        import engine
        for uc in engine.USE_CASES:
            with self.subTest(use_case=uc["title"]):
                stages = engine.build_pipeline(uc["example"])
                self.assertTrue(stages)
                self.assertEqual(stages[0].agent, "orchestrator")
                self.assertEqual(stages[-1].agent, "ea")

    def test_tools_no_longer_carry_private_business_logic(self):
        """The CrewAI tools must delegate, not re-implement.

        Checks the *code*, not the prose: the module docstrings legitimately
        mention the fixture they used to hold, so the invariant is that no
        fixture is assigned and no branching classification logic remains.
        """
        tools_dir = os.path.join(_ROOT, "src", "tools")
        for fname in ("intent_classifier_tool.py", "jurisdiction_compare_tool.py"):
            with self.subTest(file=fname):
                path = os.path.join(tools_dir, fname)
                with open(path, encoding="utf-8") as fh:
                    source = fh.read()
                self.assertIn("from skills import SKILLS", source)

                tree = ast.parse(source)
                assigned = {
                    t.id
                    for node in ast.walk(tree) if isinstance(node, ast.Assign)
                    for t in node.targets if isinstance(t, ast.Name)
                }
                self.assertNotIn("mock_data", assigned,
                                 "tool still assigns its own fixture")
                # No private decision logic: the tool should only delegate.
                branches = [n for n in ast.walk(tree)
                            if isinstance(n, (ast.If, ast.For, ast.While))]
                self.assertEqual(branches, [],
                                 f"{fname} still contains branching business logic")

    def test_jurisdiction_fixture_exists_in_exactly_one_place(self):
        """The literal figures must live only in the gated skill."""
        hits = []
        for rel in ("src/engine.py", "src/tools/jurisdiction_compare_tool.py",
                    "src/skills/jurisdiction_compare.py"):
            with open(os.path.join(_ROOT, rel), encoding="utf-8") as fh:
                if "$2,500" in fh.read():
                    hits.append(rel)
        self.assertEqual(hits, ["src/skills/jurisdiction_compare.py"],
                         f"jurisdiction fixture duplicated in: {hits}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
