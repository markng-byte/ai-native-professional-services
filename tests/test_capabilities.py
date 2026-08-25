"""
Layer 2 — tool contract evaluation.

Per master prompt §13 this layer tests **schema, input validation,
authorization, output contract, error handling, correlation IDs and audit
references** for every Tier 1 capability. It is distinct from:

  * Layer 1 (regression) — ``run_evals.py``, the protected skill baseline; and
  * Layer 4 (runtime validation) — validating *live* outputs before delivery,
    which will reuse ``contracts.validate_envelope`` unchanged.

Standard library only (``unittest``), matching the repo's dependency-free CI.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from capabilities import CAPABILITIES                      # noqa: E402
from capabilities.contracts import RESULT_CONTRACTS, validate_envelope  # noqa: E402
from capabilities.errors import (                          # noqa: E402
    ERR_CLIENT_NOT_FOUND,
    ERR_NOT_AUTHORIZED,
    ERR_OPPORTUNITY_NOT_FOUND,
    ERR_UNKNOWN_ACTOR,
    ERR_VALIDATION,
)
from crm.fixtures import RM_DAVID, RM_SARAH                # noqa: E402

RM = {"rm_id": RM_SARAH}
OTHER_RM = {"rm_id": RM_DAVID}

# Client CLT-001234 belongs to RM_SARAH; CLT-005567 belongs to RM_DAVID.
OWNED_CLIENT = "CLT-001234"
FOREIGN_CLIENT = "CLT-005567"
OWNED_OPP = "OPP-1001"
STALLED_OPP = "OPP-1002"
FOREIGN_OPP = "OPP-2001"

# Capabilities keyed by the primary identifier they require.
CLIENT_CAPS = [
    "get_rm_client_context", "get_client_history", "get_open_tasks",
    "get_client_engagements", "get_client_documents", "get_renewal_status",
]


def call(name: str, **payload):
    return CAPABILITIES[name]({"actor": RM, **payload})


class TestRegistry(unittest.TestCase):
    def test_all_capabilities_have_a_result_contract(self):
        # RESULT_CONTRACTS is a *shared* registry: Tier 2 RM workflows register
        # their contracts into it so one validate_envelope serves every tier
        # (and, later, Layer 4 runtime validation). The invariant this test
        # protects is therefore "every Tier 1 capability has a contract", not
        # "the registry contains only Tier 1 entries".
        missing = set(CAPABILITIES) - set(RESULT_CONTRACTS)
        self.assertEqual(missing, set(), f"capabilities without a contract: {missing}")

    def test_expected_tier1_capabilities_present(self):
        expected = {
            "search_client", "get_rm_client_context", "get_opportunity_context",
            "get_client_history", "get_open_tasks", "get_client_engagements",
            "get_client_documents", "get_renewal_status",
        }
        self.assertEqual(set(CAPABILITIES), expected)


class TestOutputContract(unittest.TestCase):
    """Every success envelope must satisfy its declared contract."""

    def test_client_capabilities_conform(self):
        for name in CLIENT_CAPS:
            with self.subTest(capability=name):
                env = call(name, client_id=OWNED_CLIENT)
                self.assertTrue(env["ok"], env.get("error"))
                valid, violations = validate_envelope(env)
                self.assertTrue(valid, f"{name}: {violations}")

    def test_search_client_conforms(self):
        env = call("search_client", query="Acme")
        self.assertTrue(env["ok"], env.get("error"))
        valid, violations = validate_envelope(env)
        self.assertTrue(valid, violations)
        self.assertGreaterEqual(env["result"]["match_count"], 1)

    def test_opportunity_context_conforms(self):
        env = call("get_opportunity_context", opportunity_id=OWNED_OPP)
        self.assertTrue(env["ok"], env.get("error"))
        valid, violations = validate_envelope(env)
        self.assertTrue(valid, violations)


class TestInputValidation(unittest.TestCase):
    def test_missing_actor_is_rejected(self):
        for name in CAPABILITIES:
            with self.subTest(capability=name):
                env = CAPABILITIES[name]({"client_id": OWNED_CLIENT})
                self.assertFalse(env["ok"])
                self.assertEqual(env["error"]["code"], ERR_VALIDATION)
                self.assertTrue(validate_envelope(env)[0])

    def test_missing_client_id_is_rejected(self):
        for name in CLIENT_CAPS:
            with self.subTest(capability=name):
                env = call(name)
                self.assertFalse(env["ok"])
                self.assertEqual(env["error"]["code"], ERR_VALIDATION)

    def test_blank_search_query_is_rejected(self):
        env = call("search_client", query="   ")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], ERR_VALIDATION)

    def test_missing_opportunity_id_is_rejected(self):
        env = call("get_opportunity_context")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], ERR_VALIDATION)


class TestAuthorization(unittest.TestCase):
    """Authorization is designed around the actor, not the tool (§21)."""

    def test_rm_cannot_read_another_rms_client(self):
        for name in CLIENT_CAPS:
            with self.subTest(capability=name):
                env = call(name, client_id=FOREIGN_CLIENT)
                self.assertFalse(env["ok"])
                self.assertEqual(env["error"]["code"], ERR_NOT_AUTHORIZED)

    def test_denial_is_explicit_not_silent_empty(self):
        """A denial must be an error, never an empty-looking success."""
        env = call("get_rm_client_context", client_id=FOREIGN_CLIENT)
        self.assertFalse(env["ok"])
        self.assertIsNone(env["result"])
        self.assertIn("assigned", env["error"]["message"])

    def test_rm_cannot_read_another_rms_opportunity(self):
        env = call("get_opportunity_context", opportunity_id=FOREIGN_OPP)
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], ERR_NOT_AUTHORIZED)

    def test_search_excludes_other_rms_clients(self):
        env = call("search_client", query="Meridian")   # belongs to RM_DAVID
        self.assertTrue(env["ok"])
        self.assertEqual(env["result"]["match_count"], 0)

        other = CAPABILITIES["search_client"]({"actor": OTHER_RM, "query": "Meridian"})
        self.assertTrue(other["ok"])
        self.assertEqual(other["result"]["match_count"], 1)

    def test_unknown_actor_is_rejected(self):
        env = CAPABILITIES["get_rm_client_context"](
            {"actor": {"rm_id": "RM-NOPE"}, "client_id": OWNED_CLIENT}
        )
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], ERR_UNKNOWN_ACTOR)

    def test_authorization_result_is_recorded_in_audit(self):
        env = call("get_rm_client_context", client_id=FOREIGN_CLIENT)
        self.assertIn("authorization", env["audit"])
        self.assertFalse(env["audit"]["authorization"]["allowed"])


class TestErrorHandling(unittest.TestCase):
    def test_unknown_client_returns_not_found(self):
        env = call("get_rm_client_context", client_id="CLT-DOES-NOT-EXIST")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], ERR_CLIENT_NOT_FOUND)

    def test_unknown_opportunity_returns_not_found(self):
        env = call("get_opportunity_context", opportunity_id="OPP-NOPE")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], ERR_OPPORTUNITY_NOT_FOUND)

    def test_error_envelopes_still_validate(self):
        env = call("get_rm_client_context", client_id="CLT-DOES-NOT-EXIST")
        valid, violations = validate_envelope(env)
        self.assertTrue(valid, violations)


class TestCorrelationAndAudit(unittest.TestCase):
    def test_supplied_correlation_id_is_preserved(self):
        env = call("get_open_tasks", client_id=OWNED_CLIENT, correlation_id="corr-abc-123")
        self.assertEqual(env["correlation_id"], "corr-abc-123")
        self.assertEqual(env["audit"]["correlation_id"], "corr-abc-123")

    def test_correlation_id_is_minted_when_absent(self):
        env = call("get_open_tasks", client_id=OWNED_CLIENT)
        self.assertTrue(env["correlation_id"])
        self.assertEqual(env["audit"]["correlation_id"], env["correlation_id"])

    def test_every_capability_emits_an_audit_ref(self):
        for name in CLIENT_CAPS:
            with self.subTest(capability=name):
                env = call(name, client_id=OWNED_CLIENT)
                self.assertTrue(env["audit"]["audit_ref"])

    def test_audit_records_actor_and_source(self):
        env = call("get_client_documents", client_id=OWNED_CLIENT)
        self.assertEqual(env["audit"]["actor_id"], RM_SARAH)
        self.assertEqual(env["audit"]["actor_type"], "RM")
        self.assertEqual(env["audit"]["data_source"], "fixtures")

    def test_audit_does_not_leak_payload_bodies(self):
        """§22: identifiers and outcomes only — no record bodies in the audit."""
        env = call("get_rm_client_context", client_id=OWNED_CLIENT)
        self.assertNotIn("result", env["audit"])
        self.assertNotIn("legal_name", env["audit"])


class TestDeterminismAndGrounding(unittest.TestCase):
    def test_capabilities_are_deterministic_apart_from_audit_ids(self):
        """Same input -> same business result (decision D4/D5: no LLM)."""
        a = call("get_opportunity_context", opportunity_id=STALLED_OPP)
        b = call("get_opportunity_context", opportunity_id=STALLED_OPP)
        self.assertEqual(a["result"], b["result"])

    def test_missing_information_is_reported_not_invented(self):
        """§11: unknowns must be surfaced explicitly."""
        env = call("get_opportunity_context", opportunity_id="OPP-1003")
        missing = env["result"]["missing_information"]
        self.assertTrue(missing)
        self.assertTrue(any("service type" in m for m in missing))

    def test_stalled_opportunity_is_flagged_with_traceable_basis(self):
        env = call("get_opportunity_context", opportunity_id=STALLED_OPP)
        aging = env["result"]["aging"]
        self.assertTrue(aging["is_stalled"])
        self.assertEqual(aging["conversion_risk"], "HIGH")
        self.assertIn("SLA", aging["basis"])   # reason is explainable, not a bare score

    def test_healthy_opportunity_is_not_flagged(self):
        env = call("get_opportunity_context", opportunity_id=OWNED_OPP)
        self.assertFalse(env["result"]["aging"]["is_stalled"])
        self.assertEqual(env["result"]["aging"]["conversion_risk"], "LOW")


class TestSkillReuse(unittest.TestCase):
    """Decision D3: the capability wraps the gated skill, it does not replace it."""

    def test_client_context_cites_the_client_lookup_skill(self):
        env = call("get_rm_client_context", client_id=OWNED_CLIENT)
        evidence = env["result"]["skill_evidence"]
        self.assertEqual(evidence["source_skill"], "client-lookup")
        self.assertEqual(evidence["match_type"], "EXACT")
        self.assertTrue(evidence["audit_log_ref"])

    def test_compliance_flags_come_from_the_skill(self):
        """CLT-009001 carries an open flag in the skill fixture; RM_DAVID owns it."""
        env = CAPABILITIES["get_rm_client_context"](
            {"actor": OTHER_RM, "client_id": "CLT-009001"}
        )
        self.assertTrue(env["ok"], env.get("error"))
        self.assertTrue(env["result"]["compliance_flags"])


class TestAdapterSeam(unittest.TestCase):
    """§6: capabilities must not be coupled to a data source."""

    def test_unusable_source_fails_loudly(self):
        """§27: a fixture must never be silently reported as Salesforce.

        Phase 4 implemented the Salesforce adapter, so selecting it without
        credentials now raises RuntimeError (unconfigured) rather than
        NotImplementedError (absent). The invariant this test protects is
        unchanged: selecting a non-fixture source must never silently hand back
        a fixture adapter.
        """
        from crm.adapters import get_adapter
        os.environ["FIRMOS_CRM_SOURCE"] = "salesforce"
        try:
            with self.assertRaises((RuntimeError, NotImplementedError)):
                get_adapter()
        finally:
            os.environ.pop("FIRMOS_CRM_SOURCE", None)

    def test_unknown_source_never_falls_back_to_fixtures(self):
        from crm.adapters import get_adapter
        os.environ["FIRMOS_CRM_SOURCE"] = "not-a-real-source"
        try:
            with self.assertRaises(NotImplementedError):
                get_adapter()
        finally:
            os.environ.pop("FIRMOS_CRM_SOURCE", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
