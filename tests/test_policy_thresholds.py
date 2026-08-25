"""
Decision-threshold policy tests (settles D1).

The thresholds that drive every RM recommendation now live in
``config/thresholds.json`` rather than in code. Three things must hold:

1. **Externalising changed nothing.** The shipped file reproduces the previous
   hardcoded behaviour exactly, so this was a refactor of *where* the numbers
   live, not a change to what the co-pilot advises.
2. **The file actually governs the advice.** Editing it must visibly change a
   risk band — otherwise it is decorative configuration and the real numbers
   are still buried somewhere.
3. **Bad policy fails loudly.** A malformed threshold would not crash; it would
   quietly produce wrong advice, which is worse.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

import policy                                              # noqa: E402
from crm.models import assess_aging                        # noqa: E402
from policy.thresholds import ThresholdError, Thresholds   # noqa: E402
from rm import RM_WORKFLOWS                                # noqa: E402

SHIPPED = os.path.join(_ROOT, "config", "thresholds.json")

BASE = {
    "stage_sla_days": {"PROSPECT": 14, "QUALIFIED": 21, "PROPOSAL": 30, "NEGOTIATION": 21},
    "high_risk_multiple": 2.0,
    "stale_activity_days": 30,
    "urgent_renewal_days": 30,
    "urgent_renewal_high_priority_days": 14,
    "high_value_amount": 50000,
}


def write_policy(tmpdir, **overrides):
    data = json.loads(json.dumps(BASE))
    data.update(overrides)
    path = os.path.join(tmpdir, "thresholds.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


class TestShippedPolicy(unittest.TestCase):
    def test_shipped_file_exists_and_loads(self):
        self.assertTrue(os.path.exists(SHIPPED), "config/thresholds.json is missing")
        t = policy.load(SHIPPED)
        self.assertEqual(t.stage_sla_days["NEGOTIATION"], 21)

    def test_shipped_file_matches_builtin_defaults(self):
        """Behaviour must not depend on whether the file was found."""
        from policy.thresholds import _BUILTIN_DEFAULTS
        shipped = policy.load(SHIPPED)
        builtin = Thresholds(dict(_BUILTIN_DEFAULTS), source="built-in")
        self.assertEqual(shipped.stage_sla_days, builtin.stage_sla_days)
        self.assertEqual(shipped.high_risk_multiple, builtin.high_risk_multiple)
        self.assertEqual(shipped.stale_activity_days, builtin.stale_activity_days)
        self.assertEqual(shipped.high_value_amount, builtin.high_value_amount)

    def test_shipped_policy_is_flagged_unratified(self):
        """Until the firm ratifies these numbers, the UI must say so."""
        t = policy.load(SHIPPED)
        self.assertFalse(t.ratified)
        self.assertIn("provisional", t.provenance)

    def test_provenance_names_the_file_and_owner(self):
        t = policy.load(SHIPPED)
        self.assertIn("thresholds.json", t.provenance)
        self.assertIn("owner", t.provenance)


class TestPolicyGovernsAdvice(unittest.TestCase):
    """The file must actually drive the recommendation, not decorate it."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._saved = os.environ.get("FIRMOS_THRESHOLDS_PATH")
        policy.reset_cache()

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("FIRMOS_THRESHOLDS_PATH", None)
        else:
            os.environ["FIRMOS_THRESHOLDS_PATH"] = self._saved
        policy.reset_cache()

    def _use(self, **overrides):
        os.environ["FIRMOS_THRESHOLDS_PATH"] = write_policy(self._tmp, **overrides)
        policy.reset_cache()

    def test_default_policy_reproduces_previous_behaviour(self):
        """64 days in a 21-day NEGOTIATION stage was HIGH before; still is."""
        self._use()
        aging = assess_aging("NEGOTIATION", 64)
        self.assertEqual(aging["sla_days"], 21)
        self.assertTrue(aging["is_stalled"])
        self.assertEqual(aging["conversion_risk"], "HIGH")

    def test_raising_the_sla_downgrades_the_risk(self):
        """A firm with a longer negotiation cycle should not see HIGH here."""
        self._use(stage_sla_days={**BASE["stage_sla_days"], "NEGOTIATION": 90})
        aging = assess_aging("NEGOTIATION", 64)
        self.assertFalse(aging["is_stalled"])
        self.assertEqual(aging["conversion_risk"], "LOW")

    def test_risk_multiple_changes_the_band(self):
        self._use(stage_sla_days={**BASE["stage_sla_days"], "NEGOTIATION": 40},
                  high_risk_multiple=5.0)
        aging = assess_aging("NEGOTIATION", 64)
        self.assertTrue(aging["is_stalled"])
        self.assertEqual(aging["conversion_risk"], "MEDIUM")

    def test_policy_change_reaches_the_rm_workflow(self):
        """End-to-end: the file governs what an RM is actually told."""
        self._use()
        strict = RM_WORKFLOWS["rm-opportunity-review"](
            {"actor": {"rm_id": "RM-001"}, "opportunity_id": "OPP-1002"})
        self.assertEqual(strict["result"]["conversion_risk"], "HIGH")

        self._use(stage_sla_days={**BASE["stage_sla_days"], "NEGOTIATION": 120})
        relaxed = RM_WORKFLOWS["rm-opportunity-review"](
            {"actor": {"rm_id": "RM-001"}, "opportunity_id": "OPP-1002"})
        self.assertEqual(relaxed["result"]["conversion_risk"], "LOW")

    def test_high_value_line_governs_the_signal(self):
        self._use(high_value_amount=1_000_000)
        env = RM_WORKFLOWS["rm-next-best-action"](
            {"actor": {"rm_id": "RM-001"}, "client_id": "CLT-002891"})
        codes = {s["code"] for s in env["result"]["other_signals"]}
        codes.add(env["result"]["signal_code"])
        self.assertNotIn("HIGH_VALUE_GOING_COLD", codes,
                         "a 95k opportunity must not be 'high value' at a 1M threshold")

    def test_every_aging_verdict_names_its_policy(self):
        self._use()
        env = RM_WORKFLOWS["rm-opportunity-review"](
            {"actor": {"rm_id": "RM-001"}, "opportunity_id": "OPP-1002"})
        self.assertTrue(env["result"]["aging"]["policy_source"])


class TestPolicyValidation(unittest.TestCase):
    """Bad policy must fail loudly rather than produce quiet bad advice."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def _expect_error(self, **overrides):
        path = write_policy(self._tmp, **overrides)
        with self.assertRaises(ThresholdError):
            policy.load(path)

    def test_missing_stage_rejected(self):
        self._expect_error(stage_sla_days={"PROSPECT": 14})

    def test_zero_or_negative_sla_rejected(self):
        self._expect_error(stage_sla_days={**BASE["stage_sla_days"], "PROPOSAL": 0})
        self._expect_error(stage_sla_days={**BASE["stage_sla_days"], "PROPOSAL": -5})

    def test_non_integer_sla_rejected(self):
        self._expect_error(stage_sla_days={**BASE["stage_sla_days"], "PROPOSAL": "thirty"})

    def test_risk_multiple_below_one_rejected(self):
        """A multiple < 1 would make HIGH trigger before MEDIUM."""
        self._expect_error(high_risk_multiple=0.5)

    def test_negative_window_rejected(self):
        self._expect_error(stale_activity_days=-1)

    def test_escalated_renewal_window_must_sit_inside_the_urgent_one(self):
        self._expect_error(urgent_renewal_days=10,
                           urgent_renewal_high_priority_days=30)

    def test_malformed_json_rejected(self):
        path = os.path.join(self._tmp, "bad.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        with self.assertRaises(ThresholdError):
            policy.load(path)

    def test_explicitly_named_missing_file_is_an_error(self):
        """Silently falling back would run on numbers nobody chose."""
        with self.assertRaises(ThresholdError):
            policy.load(os.path.join(self._tmp, "nope.json"))

    def test_missing_env_path_is_an_error(self):
        saved = os.environ.get("FIRMOS_THRESHOLDS_PATH")
        os.environ["FIRMOS_THRESHOLDS_PATH"] = os.path.join(self._tmp, "ghost.json")
        policy.reset_cache()
        try:
            with self.assertRaises(ThresholdError):
                policy.load()
        finally:
            if saved is None:
                os.environ.pop("FIRMOS_THRESHOLDS_PATH", None)
            else:
                os.environ["FIRMOS_THRESHOLDS_PATH"] = saved
            policy.reset_cache()


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestRatificationGuardrail(unittest.TestCase):
    """Ratification is a governance claim, so it must carry accountability."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def test_cannot_ratify_without_an_owner(self):
        path = write_policy(self._tmp, ratified=True,
                            policy_owner="UNASSIGNED — set before pilot use",
                            last_reviewed="2026-08-25")
        with self.assertRaises(ThresholdError) as ctx:
            policy.load(path)
        self.assertIn("policy_owner", str(ctx.exception))

    def test_cannot_ratify_without_a_review_date(self):
        path = write_policy(self._tmp, ratified=True,
                            policy_owner="Head of Corporate Services")
        with self.assertRaises(ThresholdError) as ctx:
            policy.load(path)
        self.assertIn("last_reviewed", str(ctx.exception))

    def test_properly_ratified_policy_loads_and_reads_as_firm_policy(self):
        path = write_policy(self._tmp, ratified=True,
                            policy_owner="Head of Corporate Services",
                            last_reviewed="2026-08-25")
        t = policy.load(path)
        self.assertTrue(t.ratified)
        self.assertIn("firm policy", t.provenance)
        self.assertNotIn("provisional", t.provenance)

    def test_unratified_policy_needs_no_owner(self):
        """A draft policy must still load — the warning is the point, not a block."""
        t = policy.load(write_policy(self._tmp))
        self.assertFalse(t.ratified)
