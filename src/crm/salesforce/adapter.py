"""
Salesforce implementation of :class:`crm.adapters.CRMAdapter`.

This is the Phase 4 swap the architecture was built for: the capability tools,
the RM workflows, the contracts and the evaluation layers are **unchanged**.
Only the data source moves.

    Capability Tool -> CRMAdapter -> [ FixtureCRMAdapter | SalesforceCRMAdapter ]

Two mapping problems are handled explicitly rather than glossed over:

**1. Absolute dates vs. day offsets.**
The firmOS domain model stores time-relative values as integer day offsets so
that fixtures and evals are deterministic. Salesforce returns absolute dates.
The conversion happens here, against an **injectable** ``today`` so tests are
deterministic and production simply uses the real date. This is the one place
where Salesforce-backed results legitimately vary day to day.

**2. Unmappable values are surfaced, not guessed.**
An org stage outside the configured picklist map becomes ``UNMAPPED:<name>``
rather than being coerced into a firmOS stage, because a wrong stage would
silently corrupt ageing and conversion-risk assessments.

Reads only. No create/update/delete exists here or in the transport.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional

from crm.models import (
    Activity,
    Client,
    Document,
    Engagement,
    Opportunity,
    RelationshipManager,
    Task,
)
from crm.salesforce.config import SalesforceConfig
from crm.salesforce.transport import SalesforceTransport, soql_literal


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    text = str(value)
    # Salesforce dates are YYYY-MM-DD; datetimes carry a time component.
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


class SalesforceCRMAdapter:
    """Serves the CRM domain model from a Salesforce org."""

    source_name = "salesforce"

    def __init__(self, transport: SalesforceTransport, config: SalesforceConfig,
                 today: Optional[date] = None) -> None:
        self.transport = transport
        self.config = config
        # Injectable reference date keeps day-offset conversion deterministic
        # under test; production passes nothing and gets the real today.
        self._today = today or date.today()

    # -- helpers -----------------------------------------------------------

    def _days_from_today(self, value: Optional[str]) -> Optional[int]:
        parsed = _parse_date(value)
        if parsed is None:
            return None
        return (parsed - self._today).days

    def _days_since(self, value: Optional[str]) -> Optional[int]:
        parsed = _parse_date(value)
        if parsed is None:
            return None
        return (self._today - parsed).days

    # -- relationship managers --------------------------------------------

    def get_rm(self, rm_id: str) -> Optional[RelationshipManager]:
        cfg = self.config
        rows = self.transport.query(
            f"SELECT Id, Name, Department FROM {cfg.user_object} "
            f"WHERE Id = '{soql_literal(rm_id)}' LIMIT 1"
        )
        if not rows:
            return None
        row = rows[0]
        return RelationshipManager(
            rm_id=row.get("Id", rm_id),
            full_name=row.get("Name") or "",
            department=row.get("Department") or "",
        )

    # -- clients -----------------------------------------------------------

    def _client_from_row(self, row: Dict) -> Client:
        cfg = self.config
        return Client(
            client_id=row.get("Id", ""),
            legal_name=row.get("Name") or "",
            jurisdiction=row.get(cfg.account_jurisdiction_field) or "",
            risk_rating=row.get(cfg.account_risk_field) or "UNKNOWN",
            status=row.get(cfg.account_status_field) or "ACTIVE",
            assigned_rm_id=row.get("OwnerId") or "",
            entity_number=row.get(cfg.account_entity_number_field),
            trade_names=[],
        )

    def _account_fields(self) -> str:
        cfg = self.config
        return ", ".join([
            "Id", "Name", "OwnerId",
            cfg.account_jurisdiction_field, cfg.account_risk_field,
            cfg.account_entity_number_field, cfg.account_status_field,
        ])

    def get_client(self, client_id: str) -> Optional[Client]:
        cfg = self.config
        rows = self.transport.query(
            f"SELECT {self._account_fields()} FROM {cfg.account_object} "
            f"WHERE Id = '{soql_literal(client_id)}' LIMIT 1"
        )
        return self._client_from_row(rows[0]) if rows else None

    def search_clients(self, query: str) -> List[Client]:
        cfg = self.config
        term = soql_literal((query or "").strip())
        if not term:
            return []
        rows = self.transport.query(
            f"SELECT {self._account_fields()} FROM {cfg.account_object} "
            f"WHERE Name LIKE '%{term}%' "
            f"OR {cfg.account_entity_number_field} LIKE '%{term}%' "
            f"ORDER BY Name LIMIT 50"
        )
        return [self._client_from_row(r) for r in rows]

    # -- opportunities -----------------------------------------------------

    def _opportunity_from_row(self, row: Dict) -> Opportunity:
        cfg = self.config
        days_in_stage = self._days_since(row.get(cfg.opportunity_stage_entered_field))
        return Opportunity(
            opportunity_id=row.get("Id", ""),
            client_id=row.get("AccountId") or "",
            name=row.get("Name") or "",
            stage=cfg.map_stage(row.get("StageName") or ""),
            amount=float(row.get("Amount") or 0.0),
            currency=row.get("CurrencyIsoCode") or "USD",
            service_type=row.get(cfg.opportunity_service_type_field) or "UNKNOWN",
            days_in_stage=days_in_stage if days_in_stage is not None else 0,
            assigned_rm_id=row.get("OwnerId") or "",
            expected_close_in_days=self._days_from_today(row.get("CloseDate")),
        )

    def _opportunity_fields(self) -> str:
        cfg = self.config
        return ", ".join([
            "Id", "AccountId", "Name", "StageName", "Amount", "CurrencyIsoCode",
            "CloseDate", "OwnerId",
            cfg.opportunity_service_type_field, cfg.opportunity_stage_entered_field,
        ])

    def get_opportunity(self, opportunity_id: str) -> Optional[Opportunity]:
        cfg = self.config
        rows = self.transport.query(
            f"SELECT {self._opportunity_fields()} FROM {cfg.opportunity_object} "
            f"WHERE Id = '{soql_literal(opportunity_id)}' LIMIT 1"
        )
        return self._opportunity_from_row(rows[0]) if rows else None

    def list_opportunities_for_client(self, client_id: str) -> List[Opportunity]:
        cfg = self.config
        rows = self.transport.query(
            f"SELECT {self._opportunity_fields()} FROM {cfg.opportunity_object} "
            f"WHERE AccountId = '{soql_literal(client_id)}' ORDER BY Id"
        )
        return [self._opportunity_from_row(r) for r in rows]

    # -- activities --------------------------------------------------------

    def list_activities(self, client_id: str) -> List[Activity]:
        cfg = self.config
        rows = self.transport.query(
            f"SELECT Id, AccountId, WhatId, Subject, ActivityDate, TaskSubtype, Owner.Name "
            f"FROM {cfg.task_object} "
            f"WHERE AccountId = '{soql_literal(client_id)}' AND IsClosed = true "
            f"ORDER BY ActivityDate DESC"
        )
        out: List[Activity] = []
        for row in rows:
            occurred = self._days_since(row.get("ActivityDate"))
            owner = row.get("Owner") or {}
            out.append(Activity(
                activity_id=row.get("Id", ""),
                client_id=row.get("AccountId") or client_id,
                activity_type=(row.get("TaskSubtype") or "NOTE").upper(),
                subject=row.get("Subject") or "",
                occurred_days_ago=occurred if occurred is not None else 0,
                actor=owner.get("Name") if isinstance(owner, dict) else "",
                opportunity_id=row.get("WhatId"),
            ))
        out.sort(key=lambda a: a.occurred_days_ago)
        return out

    # -- tasks -------------------------------------------------------------

    def list_tasks(self, client_id: str) -> List[Task]:
        cfg = self.config
        rows = self.transport.query(
            f"SELECT Id, AccountId, WhatId, Subject, Status, ActivityDate, OwnerId "
            f"FROM {cfg.task_object} "
            f"WHERE AccountId = '{soql_literal(client_id)}' AND IsClosed = false "
            f"ORDER BY ActivityDate"
        )
        out: List[Task] = []
        for row in rows:
            due = self._days_from_today(row.get("ActivityDate"))
            out.append(Task(
                task_id=row.get("Id", ""),
                client_id=row.get("AccountId") or client_id,
                title=row.get("Subject") or "",
                status="DONE" if (row.get("Status") == "Completed") else "OPEN",
                due_in_days=due if due is not None else 0,
                owner_rm_id=row.get("OwnerId") or "",
                opportunity_id=row.get("WhatId"),
            ))
        out.sort(key=lambda t: t.due_in_days)
        return out

    # -- engagements (custom object) ---------------------------------------

    def list_engagements(self, client_id: str) -> List[Engagement]:
        cfg = self.config
        rows = self.transport.query(
            f"SELECT Id, {cfg.engagement_account_field}, {cfg.engagement_service_type_field}, "
            f"{cfg.engagement_status_field}, {cfg.engagement_renewal_date_field} "
            f"FROM {cfg.engagement_object} "
            f"WHERE {cfg.engagement_account_field} = '{soql_literal(client_id)}' ORDER BY Id"
        )
        return [
            Engagement(
                engagement_id=row.get("Id", ""),
                client_id=row.get(cfg.engagement_account_field) or client_id,
                service_type=row.get(cfg.engagement_service_type_field) or "UNKNOWN",
                status=(row.get(cfg.engagement_status_field) or "ACTIVE").upper(),
                renewal_in_days=self._days_from_today(row.get(cfg.engagement_renewal_date_field)),
            )
            for row in rows
        ]

    # -- documents (custom object) -----------------------------------------

    def list_documents(self, client_id: str) -> List[Document]:
        cfg = self.config
        rows = self.transport.query(
            f"SELECT Id, {cfg.document_account_field}, {cfg.document_type_field}, "
            f"{cfg.document_status_field}, {cfg.document_expiry_field} "
            f"FROM {cfg.document_object} "
            f"WHERE {cfg.document_account_field} = '{soql_literal(client_id)}' ORDER BY Id"
        )
        return [
            Document(
                doc_id=row.get("Id", ""),
                client_id=row.get(cfg.document_account_field) or client_id,
                doc_type=row.get(cfg.document_type_field) or "UNKNOWN",
                status=(row.get(cfg.document_status_field) or "VALID").upper(),
                days_until_expiry=self._days_from_today(row.get(cfg.document_expiry_field)),
            )
            for row in rows
        ]
