"""
CRM data adapters.

This is the seam mandated by master prompt §6 ("Business Tool ≠ raw database
CRUD", "Skill ≠ infrastructure adapter"). Capability tools depend only on the
:class:`CRMAdapter` interface; they never see Salesforce, SOQL, HTTP, or a
fixture module.

    Capability Tool  ->  CRMAdapter  ->  (fixtures | Salesforce sandbox)

Adding the Salesforce adapter in Phase 5 means implementing this same interface
and flipping ``FIRMOS_CRM_SOURCE``. **No capability contract changes.**

The interface is intentionally *retrieval-shaped*, not CRUD-shaped: there is no
``query()``, ``create()``, ``update()`` or ``delete()`` to expose. Tier 3 write
operations are out of scope for v1 and are deliberately absent.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Protocol

from crm import fixtures
from crm.models import (
    Activity,
    Client,
    Document,
    Engagement,
    Opportunity,
    RelationshipManager,
    Task,
)


class CRMAdapter(Protocol):
    """Read-only retrieval interface over CRM transactional truth."""

    def get_rm(self, rm_id: str) -> Optional[RelationshipManager]: ...
    def get_client(self, client_id: str) -> Optional[Client]: ...
    def search_clients(self, query: str) -> List[Client]: ...
    def get_opportunity(self, opportunity_id: str) -> Optional[Opportunity]: ...
    def list_opportunities_for_client(self, client_id: str) -> List[Opportunity]: ...
    def list_activities(self, client_id: str) -> List[Activity]: ...
    def list_tasks(self, client_id: str) -> List[Task]: ...
    def list_engagements(self, client_id: str) -> List[Engagement]: ...
    def list_documents(self, client_id: str) -> List[Document]: ...


class FixtureCRMAdapter:
    """Serves the synthetic dataset in :mod:`crm.fixtures`. Default for v1."""

    source_name = "fixtures"

    def get_rm(self, rm_id: str) -> Optional[RelationshipManager]:
        return fixtures.RELATIONSHIP_MANAGERS.get(rm_id)

    def get_client(self, client_id: str) -> Optional[Client]:
        return fixtures.CLIENTS.get(client_id)

    def search_clients(self, query: str) -> List[Client]:
        q = (query or "").strip().lower()
        if not q:
            return []
        out = []
        for client in fixtures.CLIENTS.values():
            haystack = " ".join(
                [client.client_id, client.legal_name, client.entity_number or ""]
                + list(client.trade_names)
            ).lower()
            if q in haystack:
                out.append(client)
        return sorted(out, key=lambda c: c.client_id)

    def get_opportunity(self, opportunity_id: str) -> Optional[Opportunity]:
        return fixtures.OPPORTUNITIES.get(opportunity_id)

    def list_opportunities_for_client(self, client_id: str) -> List[Opportunity]:
        return sorted(
            (o for o in fixtures.OPPORTUNITIES.values() if o.client_id == client_id),
            key=lambda o: o.opportunity_id,
        )

    def list_activities(self, client_id: str) -> List[Activity]:
        return sorted(
            (a for a in fixtures.ACTIVITIES if a.client_id == client_id),
            key=lambda a: a.occurred_days_ago,
        )

    def list_tasks(self, client_id: str) -> List[Task]:
        return sorted(
            (t for t in fixtures.TASKS if t.client_id == client_id),
            key=lambda t: t.due_in_days,
        )

    def list_engagements(self, client_id: str) -> List[Engagement]:
        return sorted(
            (e for e in fixtures.ENGAGEMENTS if e.client_id == client_id),
            key=lambda e: e.engagement_id,
        )

    def list_documents(self, client_id: str) -> List[Document]:
        return sorted(
            (d for d in fixtures.DOCUMENTS if d.client_id == client_id),
            key=lambda d: d.doc_id,
        )


def get_adapter() -> CRMAdapter:
    """Select the adapter for this process.

    ``FIRMOS_CRM_SOURCE=fixtures`` (default) is the only implemented source.
    A ``salesforce`` value is rejected loudly rather than silently degrading —
    per master prompt §27, *fixture must never be reported as Salesforce*.
    """
    source = os.environ.get("FIRMOS_CRM_SOURCE", "fixtures").strip().lower()
    if source == "fixtures":
        return FixtureCRMAdapter()
    raise NotImplementedError(
        f"CRM source {source!r} is not implemented. Only 'fixtures' is available "
        "in v1; the Salesforce adapter is deferred to a later phase."
    )
