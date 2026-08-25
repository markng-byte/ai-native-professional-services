"""
Salesforce org mapping configuration.

Why this file exists
--------------------
Some of what the RM Co-pilot needs maps onto **standard** Salesforce objects
(``Account``, ``Opportunity``, ``Task``, ``User``) whose API names are stable
across orgs. The rest — engagements, KYC documents, renewals — are firmOS
concepts with **no standard equivalent**; every org names those custom objects
differently, and the opportunity ``StageName`` picklist is org-specific too.

Guessing those names would produce an adapter that silently returns nothing, or
worse, reads the wrong field. So they are **configuration, not code**: declared
here with documented defaults, overridable per org, and validated before use.

`SalesforceConfig.validate()` fails loudly on anything unresolved, so an
unconfigured org cannot masquerade as an empty one — the same principle applied
in ``crm.adapters.get_adapter`` (§27: a fixture must never be reported as
Salesforce, and an unmapped org must never be reported as an empty CRM).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List

from crm.models import (
    STAGE_CLOSED_LOST,
    STAGE_CLOSED_WON,
    STAGE_NEGOTIATION,
    STAGE_PROPOSAL,
    STAGE_PROSPECT,
    STAGE_QUALIFIED,
)

# Salesforce's out-of-the-box Opportunity stage picklist, mapped to the firmOS
# taxonomy. Orgs routinely customise this, so it is overridable.
DEFAULT_STAGE_MAP: Dict[str, str] = {
    "Prospecting": STAGE_PROSPECT,
    "Qualification": STAGE_QUALIFIED,
    "Needs Analysis": STAGE_QUALIFIED,
    "Value Proposition": STAGE_PROPOSAL,
    "Proposal/Price Quote": STAGE_PROPOSAL,
    "Negotiation/Review": STAGE_NEGOTIATION,
    "Closed Won": STAGE_CLOSED_WON,
    "Closed Lost": STAGE_CLOSED_LOST,
}


@dataclass
class SalesforceConfig:
    """Connection settings plus the org-specific object/field mapping."""

    # --- connection -------------------------------------------------------
    instance_url: str = ""
    access_token: str = ""
    api_version: str = "v60.0"

    # --- standard objects (stable across orgs) ----------------------------
    account_object: str = "Account"
    opportunity_object: str = "Opportunity"
    task_object: str = "Task"
    user_object: str = "User"

    # --- custom objects (org-specific — MUST be confirmed per org) --------
    engagement_object: str = "firmOS_Engagement__c"
    document_object: str = "firmOS_Document__c"

    # --- field mapping ----------------------------------------------------
    # Account
    account_risk_field: str = "firmOS_Risk_Rating__c"
    account_jurisdiction_field: str = "firmOS_Jurisdiction__c"
    account_entity_number_field: str = "firmOS_Entity_Number__c"
    account_status_field: str = "firmOS_Status__c"
    # Opportunity
    opportunity_service_type_field: str = "firmOS_Service_Type__c"
    opportunity_stage_entered_field: str = "firmOS_Stage_Entered_Date__c"
    # Engagement (custom)
    engagement_account_field: str = "firmOS_Account__c"
    engagement_service_type_field: str = "firmOS_Service_Type__c"
    engagement_status_field: str = "firmOS_Status__c"
    engagement_renewal_date_field: str = "firmOS_Renewal_Date__c"
    # Document (custom)
    document_account_field: str = "firmOS_Account__c"
    document_type_field: str = "firmOS_Doc_Type__c"
    document_status_field: str = "firmOS_Status__c"
    document_expiry_field: str = "firmOS_Expiry_Date__c"

    stage_map: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_STAGE_MAP))

    # Set true only once an administrator has confirmed the custom object and
    # field API names above actually exist in the target org.
    mapping_confirmed: bool = False

    # ------------------------------------------------------------------
    @classmethod
    def from_env(cls) -> "SalesforceConfig":
        """Build config from environment variables.

        Recognised: ``SF_INSTANCE_URL``, ``SF_ACCESS_TOKEN``, ``SF_API_VERSION``,
        ``SF_ENGAGEMENT_OBJECT``, ``SF_DOCUMENT_OBJECT``,
        ``SF_MAPPING_CONFIRMED``.
        """
        cfg = cls(
            instance_url=os.environ.get("SF_INSTANCE_URL", "").rstrip("/"),
            access_token=os.environ.get("SF_ACCESS_TOKEN", ""),
            api_version=os.environ.get("SF_API_VERSION", "v60.0"),
        )
        cfg.engagement_object = os.environ.get("SF_ENGAGEMENT_OBJECT", cfg.engagement_object)
        cfg.document_object = os.environ.get("SF_DOCUMENT_OBJECT", cfg.document_object)
        cfg.mapping_confirmed = (
            os.environ.get("SF_MAPPING_CONFIRMED", "").strip().lower() in ("1", "true", "yes")
        )
        return cfg

    def validate(self) -> List[str]:
        """Return the reasons this config is not usable against a live org."""
        problems: List[str] = []
        if not self.instance_url:
            problems.append("SF_INSTANCE_URL is not set")
        if not self.access_token:
            problems.append("SF_ACCESS_TOKEN is not set")
        if not self.mapping_confirmed:
            problems.append(
                "SF_MAPPING_CONFIRMED is not set — the custom object and field API "
                f"names ({self.engagement_object}, {self.document_object}) are "
                "firmOS defaults and have not been confirmed against this org. "
                "Confirm them before reading live data."
            )
        return problems

    def map_stage(self, sf_stage: str) -> str:
        """Translate an org stage name into the firmOS taxonomy.

        An unmapped stage is surfaced verbatim rather than being coerced into a
        firmOS stage — a wrong stage would silently corrupt ageing and
        conversion-risk assessments.
        """
        return self.stage_map.get(sf_stage, f"UNMAPPED:{sf_stage}")
