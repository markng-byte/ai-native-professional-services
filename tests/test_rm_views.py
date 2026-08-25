"""
Phase 5 — RM surface tests (headless).

Streamlit is not installed in this environment, so ``src/app.py`` cannot be
imported here. That is exactly why the surface was split: all logic lives in
``rm.views`` (pure view models), ``rm.session`` (control flow) and
``rm.feedback``, none of which import Streamlit. This suite covers those, and
``src/app.py`` stays a thin rendering shell.

The load-bearing test in this file is
``TestViewsDoNotReDeriveBusinessValues`` — the surface is where the triplication
documented in the Phase 0 audit would start again, so it is asserted directly.
"""

from __future__ import annotations

import ast
import json
import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from hitl import STATE_APPROVED, STATE_REJECTED, ApprovalError   # noqa: E402
from hitl.approvals import ROLE_COMPLIANCE_OFFICER, ROLE_RM      # noqa: E402
from rm import RM_WORKFLOWS                                      # noqa: E402
from rm import views                                             # noqa: E402
from rm.feedback import (                                        # noqa: E402
    VERDICT_NOT_USEFUL, VERDICT_USEFUL, read_feedback, record_feedback, summarise,
)
from rm.session import RMSession                                 # noqa: E402

RM_SARAH = "RM-001"
RM_DAVID = "RM-002"
OWNED = "CLT-001234"
BUSY = "CLT-002891"          # expired UBO doc, overdue tasks, stalled 95k opp
FOREIGN = "CLT-005567"       # belongs to RM_DAVID
COMPLIANCE_CLIENT = "CLT-009001"


def session(rm_id=RM_SARAH, client_id=OWNED) -> RMSession:
    s = RMSession()
    s.select_rm(rm_id)
    s.select_client(client_id)
    return s


class TestViewsDoNotReDeriveBusinessValues(unittest.TestCase):
    """The view renders what the workflow decided — it never recomputes it."""

    def test_next_action_values_match_the_envelope_exactly(self):
        env = RM_WORKFLOWS["rm-next-best-action"]({"actor": {"rm_id": RM_SARAH},
                                                   "client_id": BUSY})
        v = views.next_action_view(env)
        r = env["result"]
        for field in ("recommended_action", "reason", "priority", "signal_code",
                      "evidence", "required_information", "suggested_next_question"):
            with self.subTest(field=field):
                self.assertEqual(v[field], r[field])

    def test_opportunity_aging_is_copied_not_recomputed(self):
        env = RM_WORKFLOWS["rm-opportunity-review"]({"actor": {"rm_id": RM_SARAH},
                                                     "opportunity_id": "OPP-1002"})
        v = views.opportunity_review_view(env)
        aging = env["result"]["aging"]
        self.assertEqual(v["conversion_risk"], env["result"]["conversion_risk"])
        for k in ("days_in_stage", "sla_days", "over_sla_by_days", "is_stalled", "basis"):
            with self.subTest(field=k):
                self.assertEqual(v["aging"][k], aging[k])

    def test_summary_headline_comes_from_the_workflow(self):
        env = RM_WORKFLOWS["rm-client-summary"]({"actor": {"rm_id": RM_SARAH},
                                                 "client_id": OWNED})
        v = views.client_summary_view(env)
        self.assertEqual(v["headline"], env["result"]["client_summary"])

    def test_views_module_imports_no_domain_logic(self):
        """A view that imports heuristics or the CRM could re-derive values."""
        with open(os.path.join(_ROOT, "src", "rm", "views.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Import):
                for a in node.names:
                    imported.add(a.name.split(".")[0])
        for forbidden in ("heuristics", "crm", "capabilities", "skills", "streamlit"):
            with self.subTest(module=forbidden):
                self.assertNotIn(forbidden, imported,
                                 f"rm.views must not import {forbidden}")

    def test_no_view_module_imports_streamlit(self):
        for mod in ("views.py", "session.py", "feedback.py"):
            with self.subTest(module=mod):
                with open(os.path.join(_ROOT, "src", "rm", mod), encoding="utf-8") as fh:
                    self.assertNotIn("import streamlit", fh.read())


class TestNothingIsHidden(unittest.TestCase):
    """A co-pilot that quietly drops what it doesn't know is worse than silent."""

    def test_missing_information_is_carried_through(self):
        env = RM_WORKFLOWS["rm-client-summary"]({"actor": {"rm_id": RM_SARAH},
                                                 "client_id": "CLT-007823"})
        v = views.client_summary_view(env)
        self.assertEqual(v["missing_information"], env["result"]["missing_information"])
        self.assertTrue(v["missing_information"])

    def test_other_signals_are_carried_through(self):
        env = RM_WORKFLOWS["rm-next-best-action"]({"actor": {"rm_id": RM_SARAH},
                                                   "client_id": BUSY})
        v = views.next_action_view(env)
        self.assertEqual(len(v["other_signals"]), len(env["result"]["other_signals"]))
        self.assertTrue(v["other_signals"])

    def test_every_view_exposes_its_audit_identifiers(self):
        s = session(client_id=BUSY)
        for env, fn in (
            (s.client_summary(), views.client_summary_view),
            (s.next_best_action(), views.next_action_view),
            (s.generate_draft(), views.draft_view),
        ):
            with self.subTest(view=fn.__name__):
                v = fn(env)
                self.assertTrue(v["audit"]["correlation_id"])
                self.assertTrue(v["audit"]["audit_ref"])
                self.assertEqual(v["audit"]["data_source"], "fixtures")

    def test_sources_are_exposed_for_traceability(self):
        env = RM_WORKFLOWS["rm-client-summary"]({"actor": {"rm_id": RM_SARAH},
                                                 "client_id": OWNED})
        self.assertTrue(views.client_summary_view(env)["sources"])


class TestErrorAndDenialRendering(unittest.TestCase):
    def test_denial_renders_as_denial_not_empty_state(self):
        env = RM_WORKFLOWS["rm-client-summary"]({"actor": {"rm_id": RM_SARAH},
                                                 "client_id": FOREIGN})
        v = views.client_summary_view(env)
        self.assertEqual(v["kind"], "error")
        self.assertTrue(v["is_authorization_denial"])
        self.assertEqual(v["headline"], "Not authorised")

    def test_empty_search_explains_authorization_filtering(self):
        s = session()
        v = views.search_results_view(s.search("Meridian"))   # RM_DAVID's client
        self.assertEqual(v["match_count"], 0)
        self.assertIn("another RM", v["empty_note"])

    def test_successful_search_has_no_empty_note(self):
        s = session()
        v = views.search_results_view(s.search("Acme"))
        self.assertGreaterEqual(v["match_count"], 1)
        self.assertIsNone(v["empty_note"])

    def test_not_found_renders_as_error(self):
        env = RM_WORKFLOWS["rm-opportunity-review"]({"actor": {"rm_id": RM_SARAH},
                                                     "opportunity_id": "OPP-NOPE"})
        v = views.opportunity_review_view(env)
        self.assertEqual(v["kind"], "error")
        self.assertFalse(v["is_authorization_denial"])


class TestSessionControlFlow(unittest.TestCase):
    def test_switching_rm_clears_the_previous_selection(self):
        """Carrying a selection across actors would show a client picked
        under another RM's authorization."""
        s = session(client_id=OWNED)
        s.generate_draft()
        s.select_rm(RM_DAVID)
        self.assertIsNone(s.client_id)
        self.assertIsNone(s.draft_envelope)
        self.assertIsNone(s.approval_id)

    def test_switching_client_clears_the_draft(self):
        s = session()
        s.generate_draft()
        s.select_client("CLT-002891")
        self.assertIsNone(s.draft_envelope)

    def test_new_draft_invalidates_a_previous_approval(self):
        s = session(client_id=BUSY)
        s.generate_draft()
        s.submit_for_review()
        self.assertIsNotNone(s.approval_id)
        s.generate_draft()
        self.assertIsNone(s.approval_id, "a fresh draft must not inherit an approval")

    def test_cannot_submit_without_a_draft(self):
        with self.assertRaises(ValueError):
            session().submit_for_review()

    def test_cannot_decide_without_a_submission(self):
        s = session()
        s.generate_draft()
        with self.assertRaises(ValueError):
            s.decide(STATE_APPROVED, reviewer_id="x", reviewer_role=ROLE_RM)

    def test_denied_client_yields_error_envelope_not_exception(self):
        s = session(client_id=FOREIGN)
        env = s.client_summary()
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], "ERR_NOT_AUTHORIZED")


class TestApprovalLoopThroughTheSurface(unittest.TestCase):
    def test_full_loop_blocks_until_approved(self):
        s = session(client_id=OWNED)
        s.generate_draft()

        self.assertFalse(s.delivery_decision()["delivered"])
        s.submit_for_review()
        self.assertFalse(s.delivery_decision()["delivered"])
        s.decide(STATE_APPROVED, reviewer_id=RM_SARAH, reviewer_role=s.required_role())
        self.assertTrue(s.delivery_decision()["delivered"])

    def test_rejected_draft_never_delivers(self):
        s = session(client_id=OWNED)
        s.generate_draft()
        s.submit_for_review()
        s.decide(STATE_REJECTED, reviewer_id=RM_SARAH, reviewer_role=s.required_role(),
                 justification="Wrong tone for this client.")
        self.assertFalse(s.delivery_decision()["delivered"])

    def test_compliance_draft_requires_the_compliance_officer(self):
        s = session(rm_id=RM_DAVID, client_id=COMPLIANCE_CLIENT)
        s.generate_draft()
        self.assertEqual(s.required_role(), ROLE_COMPLIANCE_OFFICER)
        s.submit_for_review()
        with self.assertRaises(ApprovalError):
            s.decide(STATE_APPROVED, reviewer_id=RM_DAVID, reviewer_role=ROLE_RM)
        s.decide(STATE_APPROVED, reviewer_id="CO-1",
                 reviewer_role=ROLE_COMPLIANCE_OFFICER)
        self.assertTrue(s.delivery_decision()["delivered"])

    def test_draft_view_surfaces_the_blocking_reason(self):
        s = session(client_id=OWNED)
        env = s.generate_draft()
        v = views.draft_view(env, s.approval_record(), s.delivery_decision())
        self.assertFalse(v["gate_delivered"])
        self.assertEqual(v["gate_status"], "BLOCKED")
        self.assertTrue(v["blocked_reasons"])

    def test_draft_view_shows_never_sent_and_review_flag(self):
        s = session(client_id=OWNED)
        v = views.draft_view(s.generate_draft())
        self.assertTrue(v["requires_human_review"])
        self.assertEqual(v["delivery_status"], "DRAFT_NOT_SENT")
        self.assertIn("has not been sent", v["never_sent_notice"])

    def test_draft_view_reports_the_approval_trail(self):
        s = session(client_id=OWNED)
        env = s.generate_draft()
        s.submit_for_review()
        s.decide(STATE_APPROVED, reviewer_id=RM_SARAH, reviewer_role=s.required_role())
        v = views.draft_view(env, s.approval_record(), s.delivery_decision())
        self.assertEqual(v["approval_state"], STATE_APPROVED)
        self.assertEqual([e["event"] for e in v["events"]], ["SUBMITTED", STATE_APPROVED])
        self.assertTrue(v["gate_delivered"])


class TestFeedbackCapture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.path = os.path.join(self._tmp, "fb", "rm_feedback.jsonl")

    def test_records_a_verdict(self):
        env = RM_WORKFLOWS["rm-next-best-action"]({"actor": {"rm_id": RM_SARAH},
                                                   "client_id": BUSY})
        record_feedback(env, rm_id=RM_SARAH, verdict=VERDICT_USEFUL, path=self.path)
        entries = read_feedback(self.path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["verdict"], VERDICT_USEFUL)
        self.assertEqual(entries[0]["correlation_id"], env["correlation_id"])

    def test_rejects_an_unknown_verdict(self):
        env = RM_WORKFLOWS["rm-client-summary"]({"actor": {"rm_id": RM_SARAH},
                                                 "client_id": OWNED})
        with self.assertRaises(ValueError):
            record_feedback(env, rm_id=RM_SARAH, verdict="AMAZING", path=self.path)

    def test_does_not_store_draft_bodies_or_client_names(self):
        s = session(client_id=OWNED)
        env = s.generate_draft()
        record_feedback(env, rm_id=RM_SARAH, verdict=VERDICT_NOT_USEFUL, path=self.path)
        with open(self.path, encoding="utf-8") as fh:
            raw = fh.read()
        self.assertNotIn("Dear [CONTACT NAME]", raw)
        self.assertNotIn("Acme Global Holdings", raw)
        self.assertIn(env["correlation_id"], raw)

    def test_note_is_length_capped(self):
        env = RM_WORKFLOWS["rm-client-summary"]({"actor": {"rm_id": RM_SARAH},
                                                 "client_id": OWNED})
        entry = record_feedback(env, rm_id=RM_SARAH, verdict=VERDICT_USEFUL,
                                note="x" * 5000, path=self.path)
        self.assertEqual(len(entry["note"]), 500)

    def test_missing_log_reads_as_empty(self):
        self.assertEqual(read_feedback(os.path.join(self._tmp, "nope.jsonl")), [])

    def test_summarise_reports_useful_rate_by_signal(self):
        env = RM_WORKFLOWS["rm-next-best-action"]({"actor": {"rm_id": RM_SARAH},
                                                   "client_id": BUSY})
        record_feedback(env, rm_id=RM_SARAH, verdict=VERDICT_USEFUL, path=self.path)
        record_feedback(env, rm_id=RM_SARAH, verdict=VERDICT_NOT_USEFUL, path=self.path)
        stats = summarise(read_feedback(self.path))
        self.assertEqual(stats["total"], 2)
        self.assertAlmostEqual(stats["useful_rate"], 0.5)
        self.assertIn(env["result"]["signal_code"], stats["by_signal"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
