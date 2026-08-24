"""
Synthetic CRM dataset (v1 data source).

**This is fixture data, not Salesforce.** Per master prompt §27 the distinction
is never blurred: no production PII appears here, and every record is invented.
The Salesforce adapter (Phase 5) will serve the same model from a sandbox
without any capability-tool contract changing.

Client identifiers deliberately match the fixtures already used by the gated
``client-lookup`` skill (``src/skills/client_lookup.py``) so that
``get_rm_client_context`` can *wrap* that verified skill rather than
re-implement it (decision D3).

Two RMs exist so that cross-RM authorization denial is testable (decision D2).
"""

from __future__ import annotations

from typing import Dict, List

from crm.models import (
    Activity,
    Client,
    Document,
    Engagement,
    Opportunity,
    RelationshipManager,
    Task,
    STAGE_NEGOTIATION,
    STAGE_PROPOSAL,
    STAGE_PROSPECT,
    STAGE_QUALIFIED,
)

RM_SARAH = "RM-001"
RM_DAVID = "RM-002"

RELATIONSHIP_MANAGERS: Dict[str, RelationshipManager] = {
    RM_SARAH: RelationshipManager(RM_SARAH, "Sarah Chen", "Corporate Services"),
    RM_DAVID: RelationshipManager(RM_DAVID, "David Okafor", "Corporate Services"),
}

CLIENTS: Dict[str, Client] = {
    "CLT-001234": Client(
        client_id="CLT-001234", legal_name="Acme Global Holdings Limited",
        jurisdiction="VG", risk_rating="MEDIUM", status="ACTIVE",
        assigned_rm_id=RM_SARAH, entity_number="BVI-202300456",
        trade_names=["Acme Global"],
    ),
    "CLT-002891": Client(
        client_id="CLT-002891", legal_name="Orion Capital Partners Pte Ltd",
        jurisdiction="SG", risk_rating="MEDIUM", status="ACTIVE",
        assigned_rm_id=RM_SARAH, entity_number="SG-202100333",
        trade_names=["Orion Capital"],
    ),
    "CLT-007823": Client(
        client_id="CLT-007823", legal_name="Vertex Nominees Limited",
        jurisdiction="HK", risk_rating="MEDIUM", status="ACTIVE",
        assigned_rm_id=RM_SARAH, entity_number="HK-202200145",
        trade_names=["Vertex"],
    ),
    "CLT-000099": Client(
        client_id="CLT-000099", legal_name="Helios Legacy Group Ltd",
        jurisdiction="VG", risk_rating="LOW", status="ARCHIVED",
        assigned_rm_id=RM_SARAH, entity_number="VG-201500777",
        trade_names=["Helios Legacy"],
    ),
    # Assigned to the *other* RM — used to prove authorization denial.
    "CLT-005567": Client(
        client_id="CLT-005567", legal_name="Meridian Trust Services Ltd",
        jurisdiction="KY", risk_rating="HIGH", status="ACTIVE",
        assigned_rm_id=RM_DAVID, entity_number="KY-201900912",
        trade_names=["Meridian Trust"],
    ),
    "CLT-009001": Client(
        client_id="CLT-009001", legal_name="Sunrise Capital Ventures Ltd",
        jurisdiction="VG", risk_rating="HIGH", status="ACTIVE",
        assigned_rm_id=RM_DAVID, entity_number="VG-202400988",
        trade_names=["Sunrise Capital"],
    ),
}

OPPORTUNITIES: Dict[str, Opportunity] = {
    # Healthy, recently advanced.
    "OPP-1001": Opportunity(
        opportunity_id="OPP-1001", client_id="CLT-001234",
        name="BVI holding structure — 2 subsidiaries", stage=STAGE_PROPOSAL,
        amount=18000.0, currency="USD", service_type="COMPANY_FORMATION",
        days_in_stage=11, assigned_rm_id=RM_SARAH, expected_close_in_days=25,
    ),
    # Stalled: 64d in a 21d-SLA stage -> HIGH conversion risk.
    "OPP-1002": Opportunity(
        opportunity_id="OPP-1002", client_id="CLT-002891",
        name="Singapore fund administration mandate", stage=STAGE_NEGOTIATION,
        amount=95000.0, currency="USD", service_type="FUND_ADMIN",
        days_in_stage=64, assigned_rm_id=RM_SARAH, expected_close_in_days=-9,
    ),
    # Early stage, deliberately incomplete (no amount/close date signal).
    "OPP-1003": Opportunity(
        opportunity_id="OPP-1003", client_id="CLT-007823",
        name="HK redomiciliation enquiry", stage=STAGE_PROSPECT,
        amount=0.0, currency="USD", service_type="UNKNOWN",
        days_in_stage=6, assigned_rm_id=RM_SARAH, expected_close_in_days=None,
    ),
    # Mildly ageing: 27d in a 21d-SLA stage -> MEDIUM.
    "OPP-1004": Opportunity(
        opportunity_id="OPP-1004", client_id="CLT-001234",
        name="Annual compliance retainer renewal", stage=STAGE_QUALIFIED,
        amount=7500.0, currency="USD", service_type="REGISTERED_AGENT",
        days_in_stage=27, assigned_rm_id=RM_SARAH, expected_close_in_days=14,
    ),
    # Belongs to the other RM.
    "OPP-2001": Opportunity(
        opportunity_id="OPP-2001", client_id="CLT-009001",
        name="Cayman fund launch", stage=STAGE_PROPOSAL,
        amount=140000.0, currency="USD", service_type="FUND_FORMATION",
        days_in_stage=9, assigned_rm_id=RM_DAVID, expected_close_in_days=30,
    ),
}

ACTIVITIES: List[Activity] = [
    Activity("ACT-01", "CLT-001234", "MEETING", "Structure walkthrough with CFO", 4, "Sarah Chen", "OPP-1001"),
    Activity("ACT-02", "CLT-001234", "EMAIL", "Sent fee schedule", 2, "Sarah Chen", "OPP-1001"),
    Activity("ACT-03", "CLT-002891", "EMAIL", "Chased signature on term sheet", 38, "Sarah Chen", "OPP-1002"),
    Activity("ACT-04", "CLT-002891", "CALL", "Discussed fee objection", 51, "Sarah Chen", "OPP-1002"),
    Activity("ACT-05", "CLT-007823", "NOTE", "Inbound enquiry via website", 6, "System", "OPP-1003"),
    Activity("ACT-06", "CLT-001234", "NOTE", "Renewal reminder logged", 9, "System", "OPP-1004"),
    Activity("ACT-07", "CLT-009001", "MEETING", "Fund structure kickoff", 3, "David Okafor", "OPP-2001"),
]

TASKS: List[Task] = [
    Task("TSK-01", "CLT-001234", "Send engagement letter for signature", "OPEN", 3, RM_SARAH, "OPP-1001"),
    Task("TSK-02", "CLT-002891", "Escalate stalled negotiation to Department Head", "OPEN", -12, RM_SARAH, "OPP-1002"),
    Task("TSK-03", "CLT-002891", "Collect updated UBO declaration", "OPEN", -4, RM_SARAH, "OPP-1002"),
    Task("TSK-04", "CLT-007823", "Qualify enquiry — capture service scope + budget", "OPEN", 2, RM_SARAH, "OPP-1003"),
    Task("TSK-05", "CLT-001234", "Confirm renewal pricing", "DONE", -20, RM_SARAH, "OPP-1004"),
    Task("TSK-06", "CLT-009001", "Prepare fund launch checklist", "OPEN", 5, RM_DAVID, "OPP-2001"),
]

ENGAGEMENTS: List[Engagement] = [
    Engagement("ENG-01", "CLT-001234", "REGISTERED_AGENT", "ACTIVE", renewal_in_days=21),
    Engagement("ENG-02", "CLT-001234", "COMPANY_FORMATION", "ACTIVE", renewal_in_days=180),
    Engagement("ENG-03", "CLT-002891", "ACCOUNTING", "ACTIVE", renewal_in_days=95),
    Engagement("ENG-04", "CLT-002891", "ANNUAL_RENEWAL", "ACTIVE", renewal_in_days=8),
    Engagement("ENG-05", "CLT-007823", "REGISTERED_AGENT", "ACTIVE", renewal_in_days=140),
    Engagement("ENG-06", "CLT-000099", "REGISTERED_AGENT", "ENDED", renewal_in_days=None),
    Engagement("ENG-07", "CLT-009001", "COMPANY_FORMATION", "PENDING", renewal_in_days=None),
]

DOCUMENTS: List[Document] = [
    Document("DOC-01", "CLT-001234", "PASSPORT", "EXPIRING", 12),
    Document("DOC-02", "CLT-001234", "PROOF_OF_ADDRESS", "VALID", 300),
    Document("DOC-03", "CLT-002891", "UBO_DECLARATION", "EXPIRED", -30),
    Document("DOC-04", "CLT-002891", "PASSPORT", "VALID", 420),
    Document("DOC-05", "CLT-007823", "PASSPORT", "MISSING", None),
    Document("DOC-06", "CLT-007823", "PROOF_OF_ADDRESS", "MISSING", None),
    Document("DOC-07", "CLT-009001", "PASSPORT", "VALID", 500),
]
