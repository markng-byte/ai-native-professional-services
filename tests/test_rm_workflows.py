"""
Layer 3 — agent workflow evaluation (plus Tier 2 contract checks).

Two things run here:

* **Layer 3 scenarios** — the realistic RM situations declared in
  ``rm_workflow_scenarios.json``, asserted with the shared matcher
  (``src/evals/matcher.py``). Keeping them declarative means the scenarios stay
  reviewable by non-engineers while still being enforced in CI.
* **Tier 2 contract + invariant tests** — envelope conformance, authorization
  propagation, determinism, grounding, and the human-in-the-loop invariants.

Layer 1 (skill regression) and Layer 2 (capability contracts) remain separate
suites; this layer sits above both.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from capabilities.contracts import validate_envelope   # noqa: E402
from capabilities.errors import (                      # noqa: E402
    ERR_NOT_AUTHORIZED,
    ERR_OPPORTUNITY_NOT_FOUND,
    ERR_VALIDATION,
)
from evals.matcher import check_case                   # noqa: E402
from rm import RM_WORKFLOWS                            # noqa: E402

_SCENARIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "rm_workflow_scenarios.json")

with open(_SCENARIO_FILE, "r", encoding="utf-8") as _fh:
    SUITE = json.load(_fh)

ACTORS = SUITE["actors"]
RM = ACTORS["RM_SARAH"]
OTHER_RM = ACTORS["RM_DAVID"]

OWNED_CLIENT = "CLT-001234"
FOREIGN_CLIENT = "CLT-005567"      # belongs to RM_DAVID
FOREIGN_OPP = "OPP-2001"           # belongs to RM_DAVID
STALLED_OPP = "OPP-1002"


def run(workflow: str, actor=RM, **params):
    return RM_WORKFLOWS[workflow]({"actor": actor, **params})


class TestLayer3Scenarios(unittest.TestCase):
    """Every declared RM scenario must pass."""

    def test_all_scenarios(self):
        for sc in SUITE["scenarios"]:
            with self.subTest(scenario=sc["id"], name=sc["name"]):
                actor = ACTORS[sc["actor"]]
                env = RM_WORKFLOWS[sc["workflow"]]({"actor": actor, **sc["input"]})
                self.assertTrue(
                    env["ok"],
                    f"{sc['id']} {sc['name']}: workflow errored: {env.get('error')}",
                )
                passed, failures = check_case(env["result"], sc["expected_output"])
                self.assertTrue(
                    passed,
                    f"{sc['id']} {sc['name']} — {sc['rationale']}\n  " + "\n  ".join(failures),
                )

    def test_suite_covers_every_workflow(self):
        covered = {sc["workflow"] for sc in SUITE["scenarios"]}
        self.assertEqual(covered, set(RM_WORKFLOWS))


class TestWorkflowContracts(unittest.TestCase):
    def test_success_envelopes_conform(self):
        cases = [
            ("rm-client-summary", {"client_id": OWNED_CLIENT}),
            ("rm-next-best-action", {"client_id": OWNED_CLIENT}),
            ("rm-opportunity-review", {"opportunity_id": STALLED_OPP}),
            ("rm-followup-draft", {"client_id": OWNED_CLIENT}),
        ]
        for wf, params in cases:
            with self.subTest(workflow=wf):
                env = run(wf, **params)
                self.assertTrue(env["ok"], env.get("error"))
                valid, violations = validate_envelope(env)
                self.assertTrue(valid, f"{wf}: {violations}")

    def test_missing_actor_rejected(self):
        for wf in RM_WORKFLOWS:
            with self.subTest(workflow=wf):
                env = RM_WORKFLOWS[wf]({"client_id": OWNED_CLIENT,
                                        "opportunity_id": STALLED_OPP})
                self.assertFalse(env["ok"])
                self.assertEqual(env["error"]["code"], ERR_VALIDATION)
                self.assertTrue(validate_envelope(env)[0])

    def test_missing_identifier_rejected(self):
        for wf in ("rm-client-summary", "rm-next-best-action", "rm-followup-draft"):
            with self.subTest(workflow=wf):
                env = run(wf)
                self.assertFalse(env["ok"])
                self.assertEqual(env["error"]["code"], ERR_VALIDATION)
        env = run("rm-opportunity-review")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], ERR_VALIDATION)

    def test_unknown_opportunity_relays_not_found(self):
        env = run("rm-opportunity-review", opportunity_id="OPP-NOPE")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], ERR_OPPORTUNITY_NOT_FOUND)


class TestAuthorizationPropagation(unittest.TestCase):
    """A denial inside any capability must abort the workflow (§21)."""

    def test_client_workflows_deny_foreign_client(self):
        for wf in ("rm-client-summary", "rm-next-best-action", "rm-followup-draft"):
            with self.subTest(workflow=wf):
                env = run(wf, client_id=FOREIGN_CLIENT)
                self.assertFalse(env["ok"])
                self.assertEqual(env["error"]["code"], ERR_NOT_AUTHORIZED)
                self.assertIsNone(env["result"])

    def test_opportunity_review_denies_foreign_opportunity(self):
        env = run("rm-opportunity-review", opportunity_id=FOREIGN_OPP)
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], ERR_NOT_AUTHORIZED)

    def test_denial_records_originating_capability(self):
        env = run("rm-client-summary", client_id=FOREIGN_CLIENT)
        self.assertIn("relayed_from_capability", env["audit"])
        self.assertTrue(env["audit"]["relayed_from_capability"])

    def test_no_partial_answer_on_denial(self):
        """A denied workflow must not leak data gathered before the denial."""
        env = run("rm-followup-draft", client_id=FOREIGN_CLIENT)
        self.assertIsNone(env["result"])


class TestHumanInTheLoopInvariants(unittest.TestCase):
    """Governance rows 4/5/7 — the agent drafts; the human reviews and sends."""

    def test_draft_always_requires_review(self):
        for client_id in ("CLT-001234", "CLT-002891", "CLT-007823"):
            with self.subTest(client_id=client_id):
                env = run("rm-followup-draft", client_id=client_id)
                self.assertTrue(env["result"]["requires_human_review"])
                self.assertEqual(env["result"]["delivery_status"], "DRAFT_NOT_SENT")

    def test_draft_is_marked_internal_and_unsent(self):
        env = run("rm-followup-draft", client_id=OWNED_CLIENT)
        self.assertIn("NOT SENT", env["result"]["draft"])

    def test_no_workflow_can_send_anything(self):
        """v1 exposes no delivery/execute surface at all (Tier 3 deferred)."""
        import rm.workflows as wfmod
        forbidden = ("send", "email", "dispatch", "deliver", "post_to")
        exported = [n for n in dir(wfmod) if not n.startswith("_")]
        for name in exported:
            self.assertFalse(
                any(f in name.lower() for f in forbidden),
                f"unexpected delivery-shaped export: {name}",
            )

    def test_unknown_placeholders_are_visible_not_guessed(self):
        env = run("rm-followup-draft", client_id=OWNED_CLIENT)
        self.assertIn("[CONTACT NAME]", env["result"]["draft"])


class TestGroundingAndDeterminism(unittest.TestCase):
    def test_workflows_are_deterministic(self):
        a = run("rm-next-best-action", client_id="CLT-002891")
        b = run("rm-next-best-action", client_id="CLT-002891")
        self.assertEqual(a["result"], b["result"])

    def test_every_result_cites_its_sources(self):
        for wf, params in [
            ("rm-client-summary", {"client_id": OWNED_CLIENT}),
            ("rm-next-best-action", {"client_id": OWNED_CLIENT}),
            ("rm-opportunity-review", {"opportunity_id": STALLED_OPP}),
            ("rm-followup-draft", {"client_id": OWNED_CLIENT}),
        ]:
            with self.subTest(workflow=wf):
                env = run(wf, **params)
                self.assertTrue(env["result"]["sources"])

    def test_recommendation_always_carries_evidence(self):
        for client_id in ("CLT-001234", "CLT-002891", "CLT-007823", "CLT-000099"):
            with self.subTest(client_id=client_id):
                env = run("rm-next-best-action", client_id=client_id)
                self.assertTrue(env["ok"], env.get("error"))
                self.assertTrue(env["result"]["evidence"],
                                "a recommendation without evidence is not auditable")
                self.assertTrue(env["result"]["reason"])

    def test_draft_facts_are_attributed_to_a_source(self):
        env = run("rm-followup-draft", client_id="CLT-002891")
        for fact in env["result"]["supporting_facts"]:
            self.assertIn("source", fact)
            self.assertTrue(fact["source"])

    def test_compliance_flag_outranks_commercial_signals(self):
        """Severity ordering must not be gameable by pipeline pressure."""
        env = RM_WORKFLOWS["rm-next-best-action"](
            {"actor": OTHER_RM, "client_id": "CLT-009001"}
        )
        self.assertEqual(env["result"]["priority"], "CRITICAL")
        self.assertEqual(env["result"]["signal_code"], "COMPLIANCE_FLAG_OPEN")

    def test_archived_client_does_not_fabricate_pipeline(self):
        env = run("rm-next-best-action", client_id="CLT-000099")
        self.assertTrue(env["ok"], env.get("error"))
        self.assertEqual(env["result"]["signal_code"], "NO_OPEN_OPPORTUNITY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
