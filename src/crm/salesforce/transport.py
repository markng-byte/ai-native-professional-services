"""
Salesforce query transport.

The adapter depends on this narrow interface rather than on an HTTP client, so
the mapping logic is fully testable without a live org — and so a recorded or
stubbed transport can stand in during CI.

Only **reads** are exposed. There is no create/update/delete method anywhere in
this module: Tier 3 write operations are deferred, and an interface that cannot
express a mutation cannot accidentally perform one.
"""

from __future__ import annotations

from typing import Dict, List, Protocol
from urllib.parse import quote


class SalesforceTransport(Protocol):
    """Executes a SOQL query and returns the ``records`` array."""

    def query(self, soql: str) -> List[Dict]: ...


def soql_literal(value: str) -> str:
    """Escape a value for safe inclusion in a SOQL string literal.

    Client identifiers reach these queries from request payloads, so
    interpolating them unescaped would be a SOQL-injection hole. Salesforce
    requires backslashes and single quotes to be escaped; newline and NUL are
    escaped too so a crafted id cannot break out of the literal.
    """
    if value is None:
        return ""
    out = str(value)
    out = out.replace("\\", "\\\\")
    out = out.replace("'", "\\'")
    out = out.replace("\n", "\\n").replace("\r", "\\r").replace("\0", "")
    return out


class HttpSalesforceTransport:
    """REST transport over the Salesforce Query API.

    ``requests`` is imported lazily so that importing this module — and running
    the whole test suite against the stub transport — never requires the
    dependency.
    """

    def __init__(self, instance_url: str, access_token: str, api_version: str = "v60.0",
                 timeout: int = 30) -> None:
        self.instance_url = instance_url.rstrip("/")
        self.access_token = access_token
        self.api_version = api_version
        self.timeout = timeout

    def query(self, soql: str) -> List[Dict]:
        try:
            import requests
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "The Salesforce HTTP transport requires the 'requests' package."
            ) from exc

        url = f"{self.instance_url}/services/data/{self.api_version}/query"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        records: List[Dict] = []
        params = {"q": soql}

        while True:
            response = requests.get(url, headers=headers, params=params,
                                    timeout=self.timeout)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Salesforce query failed ({response.status_code}): {response.text[:300]}"
                )
            body = response.json()
            records.extend(body.get("records", []))
            next_url = body.get("nextRecordsUrl")
            if not next_url or body.get("done", True):
                break
            # Follow pagination; nextRecordsUrl is already a full path.
            url = f"{self.instance_url}{next_url}"
            params = None

        return records


class StubSalesforceTransport:
    """Deterministic in-memory transport for tests.

    Matches a query by the object name in its ``FROM`` clause and returns the
    canned records registered for it. Records the SOQL it was given so tests can
    assert on query construction (including that identifiers were escaped).
    """

    def __init__(self, records_by_object: Dict[str, List[Dict]] | None = None) -> None:
        self.records_by_object = records_by_object or {}
        self.queries: List[str] = []

    def query(self, soql: str) -> List[Dict]:
        self.queries.append(soql)
        upper = soql.upper()
        idx = upper.rfind(" FROM ")
        if idx == -1:
            return []
        obj = soql[idx + 6:].strip().split()[0]
        return list(self.records_by_object.get(obj, []))
