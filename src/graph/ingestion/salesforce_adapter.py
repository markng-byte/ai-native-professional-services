"""
Salesforce ingestion adapter (Stage 1 of GRAPHRAG_INDEXING_PIPELINE.md).

STUB: defines the contract for pulling Clients, Service_Mandates and related
records out of Salesforce and mapping them to the graph schema. Wire real
credentials (SF_* env vars) and the `simple-salesforce` client to activate.

Usage (once implemented):
    from graph.ingestion.salesforce_adapter import SalesforceAdapter
    from graph.engine import get_engine
    SalesforceAdapter().sync(get_engine().backend)
"""

from __future__ import annotations

import os
from typing import Dict, List

from ..backends.base import GraphBackend


class SalesforceAdapter:
    """Maps Salesforce objects → graph nodes/edges per GRAPH_SCHEMA.md.

    Field mapping (Salesforce → graph):
      Account            → Client            (Id→client_id, Name→full_legal_name)
      Contact            → Individual        (Id→individual_id, Name→full_name)
      Service_Mandate__c → Service_Mandate   (renewal date, service type, status)
      AccountContactRel  → IS_DIRECTOR_OF / OWNS edges
    """

    def __init__(self, instance_url: str = "", token: str = ""):
        self.instance_url = instance_url or os.getenv("SF_INSTANCE_URL", "")
        self.token = token or os.getenv("SF_ACCESS_TOKEN", "")

    # ---- connection -------------------------------------------------------
    def is_configured(self) -> bool:
        return bool(self.instance_url and self.token)

    def _client(self):
        # from simple_salesforce import Salesforce
        # return Salesforce(instance_url=self.instance_url, session_id=self.token)
        raise NotImplementedError(
            "Salesforce client not wired. Install `simple-salesforce`, set "
            "SF_INSTANCE_URL + SF_ACCESS_TOKEN, and implement _client()/fetch_*()."
        )

    # ---- extraction (Stage 2) --------------------------------------------
    def fetch_accounts(self) -> List[Dict]:
        """SOQL: SELECT Id, Name, ... FROM Account → Client nodes. TODO."""
        raise NotImplementedError

    def fetch_mandates(self) -> List[Dict]:
        """SOQL: SELECT Id, Service_Type__c, Renewal_Date__c, Status__c FROM Service_Mandate__c. TODO."""
        raise NotImplementedError

    # ---- load (Stage 4) ---------------------------------------------------
    def sync(self, backend: GraphBackend) -> Dict:
        """Pull from Salesforce and upsert into the graph. Returns load stats."""
        if not self.is_configured():
            return {"status": "skipped", "reason": "SF_INSTANCE_URL / SF_ACCESS_TOKEN not set"}
        # account → Client
        for acc in self.fetch_accounts():
            backend.add_node(acc["Id"], "Client", {
                "client_id": acc["Id"],
                "full_legal_name": acc.get("Name"),
                "jurisdiction_of_incorp": acc.get("Jurisdiction__c"),
                "risk_rating": acc.get("Risk_Rating__c", "LOW"),
            })
        # mandate → Service_Mandate + HAS_MANDATE edge
        for m in self.fetch_mandates():
            backend.add_node(m["Id"], "Service_Mandate", {
                "mandate_id": m["Id"],
                "service_type": m.get("Service_Type__c"),
                "renewal_date": m.get("Renewal_Date__c"),
                "status": m.get("Status__c", "active"),
                "client_name": m.get("Account_Name__c"),
            })
            if m.get("AccountId"):
                backend.add_edge(m["AccountId"], m["Id"], "HAS_MANDATE", {})
        return backend.stats()
