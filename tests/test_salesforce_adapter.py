"""
Phase 4 — Salesforce adapter tests.

Three concerns:

* **Contract parity** — the Salesforce adapter must satisfy the same
  ``CRMAdapter`` interface and produce the same domain types as the fixture
  adapter, so that capability contracts and every evaluation layer are unchanged
  by the swap. This is the property the whole adapter-seam design exists to
  guarantee.
* **Mapping correctness** — absolute Salesforce dates become deterministic day
  offsets; unmapped stages are surfaced rather than guessed; identifiers are
  escaped into SOQL.
* **Fail-loud configuration** — an unconfigured org must never look like an
  empty CRM.

All of this runs against a **stub transport**, so no credentials are required.
A separate credential-gated tier (skipped by default) exercises a real sandbox
when ``FIRMOS_SF_INTEGRATION=1`` and credentials are present.
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import date

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from capabilities import CAPABILITIES                              # noqa: E402
from capabilities.contracts import validate_envelope               # noqa: E402
from crm.adapters import CRMAdapter, FixtureCRMAdapter, get_adapter  # noqa: E402
from crm.models import (                                           # noqa: E402
    Activity, Client, Document, Engagement, Opportunity, Task,
    STAGE_NEGOTIATION, STAGE_PROPOSAL,
)
from crm.salesforce import (                                       # noqa: E402
    SalesforceCRMAdapter, SalesforceConfig, StubSalesforceTransport, soql_literal,
)

TODAY = date(2026, 6, 1)          # fixed reference date -> deterministic offsets
ACC = "001AAAAAAAAAAAAAAA"
OPP = "006AAAAAAAAAAAAAAA"
RM_ID = "005AAAAAAAAAAAAAAA"


def make_config() -> SalesforceConfig:
    cfg = SalesforceConfig(instance_url="https://example.my.salesforce.com",
                           access_token="token", mapping_confirmed=True)
    return cfg


def make_adapter(cfg=None, **records) -> SalesforceCRMAdapter:
    cfg = cfg or make_config()
    transport = StubSalesforceTransport({
        cfg.user_object: records.get("users", []),
        cfg.account_object: records.get("accounts", []),
        cfg.opportunity_object: records.get("opportunities", []),
        cfg.task_object: records.get("tasks", []),
        cfg.engagement_object: records.get("engagements", []),
        cfg.document_object: records.get("documents", []),
    })
    return SalesforceCRMAdapter(transport, cfg, today=TODAY)


ACCOUNT_ROW = {
    "Id": ACC, "Name": "Acme Global Holdings Limited", "OwnerId": RM_ID,
    "firmOS_Jurisdiction__c": "VG", "firmOS_Risk_Rating__c": "MEDIUM",
    "firmOS_Entity_Number__c": "BVI-202300456", "firmOS_Status__c": "ACTIVE",
}
OPPORTUNITY_ROW = {
    "Id": OPP, "AccountId": ACC, "Name": "BVI holding structure",
    "StageName": "Negotiation/Review", "Amount": 95000.0, "CurrencyIsoCode": "USD",
    "CloseDate": "2026-05-23",                       # 9 days before TODAY
    "OwnerId": RM_ID, "firmOS_Service_Type__c": "FUND_ADMIN",
    "firmOS_Stage_Entered_Date__c": "2026-03-29",    # 64 days before TODAY
}


class TestInterfaceParity(unittest.TestCase):
    """The swap must not change what callers can rely on."""

    def test_salesforce_adapter_implements_the_full_interface(self):
        required = [m for m in dir(CRMAdapter) if not m.startswith("_")]
        # Protocol members are the retrieval verbs the capabilities call.
        for name in ("get_rm", "get_client", "search_clients", "get_opportunity",
                     "list_opportunities_for_client", "list_activities",
                     "list_tasks", "list_engagements", "list_documents"):
            with self.subTest(method=name):
                self.assertTrue(callable(getattr(SalesforceCRMAdapter, name, None)),
                                f"SalesforceCRMAdapter is missing {name}")

    def test_both_adapters_expose_identical_method_sets(self):
        def verbs(cls):
            return {n for n in dir(cls)
                    if not n.startswith("_") and callable(getattr(cls, n, None))}
        self.assertEqual(verbs(FixtureCRMAdapter), verbs(SalesforceCRMAdapter))

    def test_neither_adapter_exposes_a_write_operation(self):
        """Tier 3 is deferred; an interface without mutations cannot mutate."""
        for cls in (FixtureCRMAdapter, SalesforceCRMAdapter):
            with self.subTest(adapter=cls.__name__):
                for verb in ("create", "update", "delete", "insert", "upsert", "query"):
                    self.assertFalse(
                        any(verb in n.lower() for n in dir(cls) if not n.startswith("_")),
                        f"{cls.__name__} exposes a {verb}-shaped method",
                    )

    def test_returns_the_same_domain_types_as_fixtures(self):
        adapter = make_adapter(accounts=[ACCOUNT_ROW], opportunities=[OPPORTUNITY_ROW],
                               users=[{"Id": RM_ID, "Name": "Sarah Chen",
                                       "Department": "Corporate Services"}])
        self.assertIsInstance(adapter.get_client(ACC), Client)
        self.assertIsInstance(adapter.get_opportunity(OPP), Opportunity)
        self.assertIsInstance(adapter.list_opportunities_for_client(ACC)[0], Opportunity)

        fixture = FixtureCRMAdapter()
        self.assertIsInstance(fixture.get_client("CLT-001234"), Client)


class TestDateMapping(unittest.TestCase):
    """Absolute Salesforce dates -> deterministic integer day offsets."""

    def test_days_in_stage_derived_from_stage_entered_date(self):
        adapter = make_adapter(opportunities=[OPPORTUNITY_ROW])
        opp = adapter.get_opportunity(OPP)
        self.assertEqual(opp.days_in_stage, 64)

    def test_past_close_date_becomes_negative_offset(self):
        adapter = make_adapter(opportunities=[OPPORTUNITY_ROW])
        opp = adapter.get_opportunity(OPP)
        self.assertEqual(opp.expected_close_in_days, -9)

    def test_overdue_task_maps_to_negative_due_days(self):
        adapter = make_adapter(tasks=[{
            "Id": "00TA", "AccountId": ACC, "WhatId": OPP, "Subject": "Chase signature",
            "Status": "In Progress", "ActivityDate": "2026-05-20", "OwnerId": RM_ID,
        }])
        task = adapter.list_tasks(ACC)[0]
        self.assertEqual(task.due_in_days, -12)
        self.assertEqual(task.status, "OPEN")

    def test_activity_age_is_days_ago(self):
        adapter = make_adapter(tasks=[{
            "Id": "00TB", "AccountId": ACC, "WhatId": OPP, "Subject": "Call",
            "ActivityDate": "2026-04-24", "TaskSubtype": "Call",
            "Owner": {"Name": "Sarah Chen"},
        }])
        act = adapter.list_activities(ACC)[0]
        self.assertEqual(act.occurred_days_ago, 38)
        self.assertEqual(act.activity_type, "CALL")

    def test_missing_dates_do_not_crash(self):
        adapter = make_adapter(documents=[{
            "Id": "a01", "firmOS_Account__c": ACC, "firmOS_Doc_Type__c": "PASSPORT",
            "firmOS_Status__c": "MISSING", "firmOS_Expiry_Date__c": None,
        }])
        doc = adapter.list_documents(ACC)[0]
        self.assertIsNone(doc.days_until_expiry)
        self.assertEqual(doc.status, "MISSING")

    def test_adapter_is_deterministic_for_a_fixed_today(self):
        a = make_adapter(opportunities=[OPPORTUNITY_ROW]).get_opportunity(OPP)
        b = make_adapter(opportunities=[OPPORTUNITY_ROW]).get_opportunity(OPP)
        self.assertEqual(a, b)


class TestStageMapping(unittest.TestCase):
    def test_standard_picklist_maps_to_firmos_taxonomy(self):
        adapter = make_adapter(opportunities=[OPPORTUNITY_ROW])
        self.assertEqual(adapter.get_opportunity(OPP).stage, STAGE_NEGOTIATION)

    def test_unmapped_stage_is_surfaced_not_guessed(self):
        """A wrong stage would silently corrupt ageing and conversion risk."""
        row = dict(OPPORTUNITY_ROW, StageName="Bespoke Internal Stage")
        adapter = make_adapter(opportunities=[row])
        self.assertEqual(adapter.get_opportunity(OPP).stage,
                         "UNMAPPED:Bespoke Internal Stage")

    def test_stage_map_is_overridable_per_org(self):
        cfg = make_config()
        cfg.stage_map = {"Our Proposal Step": STAGE_PROPOSAL}
        row = dict(OPPORTUNITY_ROW, StageName="Our Proposal Step")
        adapter = make_adapter(cfg, opportunities=[row])
        self.assertEqual(adapter.get_opportunity(OPP).stage, STAGE_PROPOSAL)


class TestSoqlSafety(unittest.TestCase):
    def test_quotes_and_backslashes_are_escaped(self):
        self.assertEqual(soql_literal("O'Brien"), "O\\'Brien")
        self.assertEqual(soql_literal("a\\b"), "a\\\\b")

    def test_injection_attempt_is_neutralised_in_the_query(self):
        cfg = make_config()
        transport = StubSalesforceTransport({cfg.account_object: []})
        adapter = SalesforceCRMAdapter(transport, cfg, today=TODAY)
        adapter.get_client("x' OR Name != '")
        issued = transport.queries[-1]
        self.assertNotIn("x' OR Name != '", issued)
        self.assertIn("\\'", issued)

    def test_blank_search_returns_without_querying(self):
        cfg = make_config()
        transport = StubSalesforceTransport({cfg.account_object: [ACCOUNT_ROW]})
        adapter = SalesforceCRMAdapter(transport, cfg, today=TODAY)
        self.assertEqual(adapter.search_clients("   "), [])
        self.assertEqual(transport.queries, [])


class TestFailLoudConfiguration(unittest.TestCase):
    """An unconfigured org must never look like an empty CRM."""

    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in
                       ("FIRMOS_CRM_SOURCE", "SF_INSTANCE_URL", "SF_ACCESS_TOKEN",
                        "SF_MAPPING_CONFIRMED")}

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_salesforce_without_credentials_raises(self):
        os.environ["FIRMOS_CRM_SOURCE"] = "salesforce"
        os.environ.pop("SF_INSTANCE_URL", None)
        os.environ.pop("SF_ACCESS_TOKEN", None)
        with self.assertRaises(RuntimeError) as ctx:
            get_adapter()
        self.assertIn("SF_INSTANCE_URL", str(ctx.exception))

    def test_unconfirmed_mapping_blocks_live_reads(self):
        os.environ["FIRMOS_CRM_SOURCE"] = "salesforce"
        os.environ["SF_INSTANCE_URL"] = "https://example.my.salesforce.com"
        os.environ["SF_ACCESS_TOKEN"] = "tok"
        os.environ.pop("SF_MAPPING_CONFIRMED", None)
        with self.assertRaises(RuntimeError) as ctx:
            get_adapter()
        self.assertIn("MAPPING_CONFIRMED", str(ctx.exception))

    def test_unknown_source_raises(self):
        os.environ["FIRMOS_CRM_SOURCE"] = "airtable"
        with self.assertRaises(NotImplementedError):
            get_adapter()

    def test_default_source_is_fixtures(self):
        os.environ.pop("FIRMOS_CRM_SOURCE", None)
        self.assertEqual(get_adapter().source_name, "fixtures")

    def test_validate_lists_every_problem(self):
        problems = SalesforceConfig().validate()
        self.assertEqual(len(problems), 3)


class TestCapabilitiesUnchangedBySwap(unittest.TestCase):
    """The capability layer must work identically over either adapter."""

    def test_capability_contracts_hold_over_the_salesforce_adapter(self):
        adapter = make_adapter(
            users=[{"Id": RM_ID, "Name": "Sarah Chen", "Department": "Corporate Services"}],
            accounts=[ACCOUNT_ROW], opportunities=[OPPORTUNITY_ROW],
        )
        import capabilities.tools as tools_mod
        original = tools_mod.get_adapter
        tools_mod.get_adapter = lambda: adapter
        try:
            env = CAPABILITIES["get_rm_client_context"](
                {"actor": {"rm_id": RM_ID}, "client_id": ACC}
            )
            self.assertTrue(env["ok"], env.get("error"))
            valid, violations = validate_envelope(env)
            self.assertTrue(valid, violations)
            self.assertEqual(env["audit"]["data_source"], "salesforce")
        finally:
            tools_mod.get_adapter = original

    def test_authorization_still_applies_over_salesforce(self):
        adapter = make_adapter(
            users=[{"Id": RM_ID, "Name": "Sarah Chen", "Department": "CS"},
                   {"Id": "005OTHER", "Name": "David Okafor", "Department": "CS"}],
            accounts=[ACCOUNT_ROW],
        )
        import capabilities.tools as tools_mod
        original = tools_mod.get_adapter
        tools_mod.get_adapter = lambda: adapter
        try:
            env = CAPABILITIES["get_rm_client_context"](
                {"actor": {"rm_id": "005OTHER"}, "client_id": ACC}
            )
            self.assertFalse(env["ok"])
            self.assertEqual(env["error"]["code"], "ERR_NOT_AUTHORIZED")
        finally:
            tools_mod.get_adapter = original


@unittest.skipUnless(
    os.environ.get("FIRMOS_SF_INTEGRATION") == "1"
    and os.environ.get("SF_INSTANCE_URL")
    and os.environ.get("SF_ACCESS_TOKEN"),
    "live Salesforce sandbox integration tier — set FIRMOS_SF_INTEGRATION=1 with "
    "SF_INSTANCE_URL / SF_ACCESS_TOKEN to run",
)
class TestLiveSandboxIntegration(unittest.TestCase):
    """Credential-gated tier. Never runs in CI; ready for a real sandbox.

    This is the tier that will confirm the org mapping is correct. Until it has
    been run against a real org, the adapter is **implemented but unverified**.
    """

    def test_adapter_connects_and_returns_domain_objects(self):
        os.environ["FIRMOS_CRM_SOURCE"] = "salesforce"
        adapter = get_adapter()
        self.assertEqual(adapter.source_name, "salesforce")
        client_id = os.environ.get("FIRMOS_SF_TEST_ACCOUNT_ID")
        if not client_id:
            self.skipTest("set FIRMOS_SF_TEST_ACCOUNT_ID to exercise a real record")
        client = adapter.get_client(client_id)
        self.assertIsNotNone(client, "test account id not found in the org")
        self.assertIsInstance(client, Client)

    def test_no_stage_is_unmapped_in_the_org(self):
        """Catches picklist values the configured stage_map does not cover."""
        os.environ["FIRMOS_CRM_SOURCE"] = "salesforce"
        adapter = get_adapter()
        client_id = os.environ.get("FIRMOS_SF_TEST_ACCOUNT_ID")
        if not client_id:
            self.skipTest("set FIRMOS_SF_TEST_ACCOUNT_ID")
        for opp in adapter.list_opportunities_for_client(client_id):
            self.assertFalse(opp.stage.startswith("UNMAPPED:"),
                             f"stage picklist not mapped: {opp.stage}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
