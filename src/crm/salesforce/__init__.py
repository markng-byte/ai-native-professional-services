"""
Salesforce data adapter (Phase 4).

Implements the same ``crm.adapters.CRMAdapter`` interface as the fixture
adapter, so capability tools, RM workflows, contracts and every evaluation
layer are unchanged when the source is swapped.

Read-only by construction: neither the adapter nor the transport exposes any
create/update/delete operation.
"""

from crm.salesforce.adapter import SalesforceCRMAdapter
from crm.salesforce.config import DEFAULT_STAGE_MAP, SalesforceConfig
from crm.salesforce.transport import (
    HttpSalesforceTransport,
    StubSalesforceTransport,
    soql_literal,
)

__all__ = [
    "SalesforceCRMAdapter", "SalesforceConfig", "DEFAULT_STAGE_MAP",
    "HttpSalesforceTransport", "StubSalesforceTransport", "soql_literal",
]
