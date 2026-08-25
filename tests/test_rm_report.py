"""
Layer 5 report tests.

The report is the only artefact in the system that answers a question no test
can: *is this useful to an RM?* Its job is to make that answer actionable
without overstating it, so the tests focus on three things:

* it attributes verdicts to the **rule** that produced them (signal code),
* it separates **correctness defects** ("wrong" — the co-pilot said something
  untrue) from **tuning** ("not useful" — unhelpful but not false), and
* it refuses to present a handful of clicks as evidence.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from hitl import ApprovalStore                                   # noqa: E402
from hitl.storage import InMemoryApprovalStorage, SqliteApprovalStorage  # noqa: E402
from rm.feedback import (                                        # noqa: E402
    VERDICT_NOT_USEFUL, VERDICT_USEFUL, VERDICT_WRONG, read_feedback, record_feedback,
)
from rm.report import (                                          # noqa: E402
    LOW_USEFUL_RATE, MIN_SAMPLE_FOR_SIGNAL, build_report, render_text,
)
from rm.session import RMSession                                 # noqa: E402
from rm import RM_WORKFLOWS                                      # noqa: E402


def entry(signal, verdict, rm="RM-001", capability="rm-next-best-action"):
    return {"signal_code": signal, "verdict": verdict, "rm_id": rm,
            "capability": capability, "correlation_id": "c", "audit_ref": "a"}


class TestReportAggregation(unittest.TestCase):
    def test_empty_log_reports_nothing_rather_than_zero_percent(self):
        report = build_report([])
        self.assertEqual(report["total_responses"], 0)
        self.assertIsNone(report["useful_rate"])
        self.assertIn("No feedback recorded yet", render_text(report))

    def test_counts_and_rate(self):
        entries = [entry("A", VERDICT_USEFUL)] * 3 + [entry("A", VERDICT_NOT_USEFUL)]
        report = build_report(entries)
        self.assertEqual(report["total_responses"], 4)
        self.assertAlmostEqual(report["useful_rate"], 0.75)

    def test_distinct_respondents_counted(self):
        entries = [entry("A", VERDICT_USEFUL, rm="RM-001"),
                   entry("A", VERDICT_USEFUL, rm="RM-002"),
                   entry("A", VERDICT_USEFUL, rm="RM-001")]
        self.assertEqual(build_report(entries)["respondents"], 2)

    def test_breakdown_is_per_signal_code(self):
        """A signal code maps to one rule, so it names what to fix."""
        entries = ([entry("RENEWAL_DUE", VERDICT_NOT_USEFUL)] * 5
                   + [entry("DOCUMENT_EXPIRED", VERDICT_USEFUL)] * 5)
        report = build_report(entries)
        codes = {s["signal_code"]: s for s in report["signals"]}
        self.assertEqual(codes["RENEWAL_DUE"]["useful_rate"], 0.0)
        self.assertEqual(codes["DOCUMENT_EXPIRED"]["useful_rate"], 1.0)

    def test_unattributed_feedback_is_kept_not_dropped(self):
        report = build_report([{"verdict": VERDICT_USEFUL, "rm_id": "RM-001"}])
        self.assertEqual(report["total_responses"], 1)
        self.assertEqual(report["signals"][0]["signal_code"], "UNATTRIBUTED")

    def test_unknown_verdicts_are_ignored(self):
        report = build_report([entry("A", "SPLENDID"), entry("A", VERDICT_USEFUL)])
        self.assertEqual(report["total_responses"], 1)


class TestCorrectnessVersusTuning(unittest.TestCase):
    """'Wrong' is a defect; 'not useful' is a preference. They are not the same."""

    def test_wrong_verdict_raises_a_correctness_concern(self):
        report = build_report([entry("DOCUMENT_EXPIRED", VERDICT_WRONG)])
        self.assertTrue(report["correctness_concerns"])
        self.assertEqual(report["correctness_concerns"][0]["signal_code"],
                         "DOCUMENT_EXPIRED")

    def test_not_useful_alone_is_not_a_correctness_concern(self):
        report = build_report([entry("RENEWAL_DUE", VERDICT_NOT_USEFUL)] * 10)
        self.assertEqual(report["correctness_concerns"], [])
        self.assertTrue(report["tuning_candidates"])

    def test_correctness_concern_is_raised_even_on_one_report(self):
        """One 'you told me something untrue' is worth investigating."""
        entries = [entry("A", VERDICT_USEFUL)] * 20 + [entry("A", VERDICT_WRONG)]
        self.assertTrue(build_report(entries)["correctness_concerns"])

    def test_low_rate_below_sample_floor_is_not_flagged_for_tuning(self):
        """Two thumbs-down is not evidence a rule is broken."""
        entries = [entry("A", VERDICT_NOT_USEFUL)] * 2
        report = build_report(entries)
        self.assertEqual(report["tuning_candidates"], [])
        self.assertFalse(report["signals"][0]["enough_data"])

    def test_low_rate_above_sample_floor_is_flagged(self):
        entries = [entry("A", VERDICT_NOT_USEFUL)] * MIN_SAMPLE_FOR_SIGNAL
        report = build_report(entries)
        self.assertEqual([s["signal_code"] for s in report["tuning_candidates"]], ["A"])

    def test_healthy_signal_is_not_flagged(self):
        entries = [entry("A", VERDICT_USEFUL)] * MIN_SAMPLE_FOR_SIGNAL
        report = build_report(entries)
        self.assertEqual(report["tuning_candidates"], [])
        self.assertEqual(report["correctness_concerns"], [])


class TestReportHonesty(unittest.TestCase):
    def test_small_sample_is_labelled_as_anecdote(self):
        text = render_text(build_report([entry("A", VERDICT_USEFUL)]))
        self.assertIn("anecdote", text)

    def test_sufficient_sample_is_not_labelled(self):
        entries = [entry("A", VERDICT_USEFUL)] * (MIN_SAMPLE_FOR_SIGNAL + 1)
        self.assertNotIn("anecdote", render_text(build_report(entries)))

    def test_rendered_report_names_the_rule_module(self):
        text = render_text(build_report([entry("A", VERDICT_USEFUL)]))
        self.assertIn("heuristics.py", text)

    def test_clean_report_says_so_explicitly(self):
        entries = [entry("A", VERDICT_USEFUL)] * MIN_SAMPLE_FOR_SIGNAL
        self.assertIn("No signal is flagged", render_text(build_report(entries)))


class TestEndToEndFromRealFeedback(unittest.TestCase):
    """Verdicts recorded from real workflow output must flow into the report."""

    def test_real_output_is_attributed_to_its_signal(self):
        path = os.path.join(tempfile.mkdtemp(), "fb.jsonl")
        env = RM_WORKFLOWS["rm-next-best-action"](
            {"actor": {"rm_id": "RM-001"}, "client_id": "CLT-002891"})
        signal = env["result"]["signal_code"]

        for _ in range(MIN_SAMPLE_FOR_SIGNAL):
            record_feedback(env, rm_id="RM-001", verdict=VERDICT_NOT_USEFUL, path=path)

        report = build_report(read_feedback(path))
        self.assertEqual(report["signals"][0]["signal_code"], signal)
        self.assertEqual([s["signal_code"] for s in report["tuning_candidates"]],
                         [signal])

    def test_draft_feedback_is_attributed_to_the_triggering_signal(self):
        path = os.path.join(tempfile.mkdtemp(), "fb.jsonl")
        env = RM_WORKFLOWS["rm-followup-draft"](
            {"actor": {"rm_id": "RM-001"}, "client_id": "CLT-002891"})
        record_feedback(env, rm_id="RM-001", verdict=VERDICT_WRONG, path=path)
        report = build_report(read_feedback(path))
        self.assertEqual(report["correctness_concerns"][0]["signal_code"],
                         env["result"]["based_on_signal"])


class TestStorageNotice(unittest.TestCase):
    """A reviewer must be told whether their decision will survive a restart."""

    def test_in_memory_warns_the_reviewer(self):
        session = RMSession(store=ApprovalStore(InMemoryApprovalStorage()))
        notice = session.storage_notice()
        self.assertFalse(notice["durable"])
        self.assertIn("lost", notice["message"])
        self.assertIn("FIRMOS_APPROVAL_DB", notice["message"])

    def test_durable_backend_confirms_retention(self):
        db = os.path.join(tempfile.mkdtemp(), "a.db")
        session = RMSession(store=ApprovalStore(SqliteApprovalStorage(db)))
        notice = session.storage_notice()
        self.assertTrue(notice["durable"])
        self.assertEqual(notice["backend"], "sqlite")
        self.assertIn("durably", notice["message"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
