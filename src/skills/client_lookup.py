"""
Skill: client-lookup

Resolves a client reference (exact ID, entity/registration number, or fuzzy
name) to a single client record enriched with risk rating, active mandates,
open compliance flags, and the last-interaction summary pulled from episodic
memory. Runs against an in-repo CRM/graph fixture instead of live Salesforce +
Neo4j.

Match semantics:
  * EXACT           — resolved deterministically (ID / entity number / exact
                      legal name).
  * FUZZY           — resolved via a trade name or near name match.
  * MULTIPLE_CANDIDATES — the query is ambiguous; the session pauses for human
                      disambiguation.
  * NOT_FOUND       — no record; the session pauses and asks for more detail.
"""

from __future__ import annotations

import uuid
from typing import Dict


def _mandate(mandate_id, service_type, status, renewal_date):
    return {
        "mandate_id": mandate_id,
        "service_type": service_type,
        "status": status,
        "renewal_date": renewal_date,
    }


CLIENTS: Dict[str, Dict] = {
    "CLT-001234": {
        "client_id": "CLT-001234",
        "legal_name": "Acme Global Holdings Limited",
        "trade_names": ["Acme Global"],
        "entity_number": "BVI-202300456",
        "risk_rating": "MEDIUM",
        "status": "ACTIVE",
        "active_mandates": [
            _mandate("MND-0001", "REGISTERED_AGENT", "ACTIVE", "2026-11-30"),
            _mandate("MND-0002", "COMPANY_FORMATION", "ACTIVE", "2026-09-15"),
        ],
        "open_compliance_flags": [],
        "last_interaction_summary": "Q1 renewal confirmed; UBO declaration refreshed 2026-02-11.",
    },
    "CLT-005567": {
        "client_id": "CLT-005567",
        "legal_name": "Meridian Trust Services Ltd",
        "trade_names": ["Meridian Trust"],
        "entity_number": "KY-201900912",
        "risk_rating": "HIGH",
        "status": "ACTIVE",
        "active_mandates": [_mandate("MND-0055", "TRUST_ADMIN", "ACTIVE", "2026-10-01")],
        "open_compliance_flags": [
            {"flag_id": "FLG-101", "type": "PEP_EXPOSURE", "status": "OPEN",
             "opened": "2026-03-02"},
        ],
        "last_interaction_summary": "Escalated PEP review pending compliance sign-off.",
    },
    "CLT-002891": {
        "client_id": "CLT-002891",
        "legal_name": "Orion Capital Partners Pte Ltd",
        "trade_names": ["Orion Capital"],
        "entity_number": "SG-202100333",
        "risk_rating": "MEDIUM",
        "status": "ACTIVE",
        "active_mandates": [
            _mandate("MND-0288", "ANNUAL_RENEWAL", "ACTIVE", "2026-07-15"),
            _mandate("MND-0289", "ACCOUNTING", "ACTIVE", "2026-12-31"),
        ],
        "open_compliance_flags": [],
        "last_interaction_summary": "Annual renewal reminder sent; awaiting board resolution.",
    },
    "CLT-000099": {
        "client_id": "CLT-000099",
        "legal_name": "Helios Legacy Group Ltd",
        "trade_names": ["Helios Legacy"],
        "entity_number": "VG-201500777",
        "risk_rating": "LOW",
        "status": "ARCHIVED",
        "active_mandates": [],
        "open_compliance_flags": [],
        "last_interaction_summary": "Client off-boarded 2025-08-01; entity struck off.",
    },
    "CLT-007823": {
        "client_id": "CLT-007823",
        "legal_name": "Vertex Nominees Limited",
        "trade_names": ["Vertex"],
        "entity_number": "HK-202200145",
        "risk_rating": "MEDIUM",
        "status": "ACTIVE",
        "active_mandates": [_mandate("MND-0781", "REGISTERED_AGENT", "ACTIVE", "2026-08-20")],
        "open_compliance_flags": [],
        "last_interaction_summary": "Discussed banking introduction to DBS; documents requested.",
    },
    "CLT-009001": {
        "client_id": "CLT-009001",
        "legal_name": "Sunrise Capital Ventures Ltd",
        "trade_names": ["Sunrise Capital"],
        "entity_number": "VG-202400988",
        "risk_rating": "HIGH",
        "status": "ACTIVE",
        "active_mandates": [_mandate("MND-0900", "COMPANY_FORMATION", "PENDING", "2026-09-01")],
        "open_compliance_flags": [
            {"flag_id": "FLG-220", "type": "HIGH_RISK_JURISDICTION", "status": "OPEN",
             "opened": "2026-05-19"},
        ],
        "last_interaction_summary": "High-risk onboarding; enhanced due diligence in progress.",
    },
}

# Fuzzy names that resolve to more than one client → human disambiguation.
_AMBIGUOUS_NAMES = {
    "asia pacific holdings": ["CLT-100001", "CLT-100002", "CLT-100003"],
}

_LEGAL_INDEX = {c["legal_name"].lower(): cid for cid, c in CLIENTS.items()}
_TRADE_INDEX = {
    t.lower(): cid for cid, c in CLIENTS.items() for t in c.get("trade_names", [])
}
_ENTITY_INDEX = {
    c["entity_number"].lower(): cid for cid, c in CLIENTS.items() if c.get("entity_number")
}


def _enrich(client: Dict, match_type: str, confidence: float, degraded: bool) -> Dict:
    return {
        "match_type": match_type,
        "lookup_confidence": confidence,
        "client_id": client["client_id"],
        "legal_name": client["legal_name"],
        "risk_rating": client["risk_rating"],
        "status": client["status"],
        "active_mandates": client["active_mandates"],
        "open_compliance_flags": client["open_compliance_flags"],
        "last_interaction_summary": client["last_interaction_summary"],
        "output_completeness": "PARTIAL" if degraded else "FULL",
        "audit_log_ref": str(uuid.uuid4()),
    }


def run(payload: Dict) -> Dict:
    mode = payload.get("lookup_mode", "FUZZY_NAME")
    query = (payload.get("lookup_query") or "").strip()
    client_id = payload.get("client_id")
    degraded = payload.get("_test_override") == "GRAPHRAG_UNAVAILABLE"

    if mode == "EXACT_ID":
        client = CLIENTS.get(client_id or query)
        if not client:
            return {"match_type": "NOT_FOUND", "output_completeness": "FULL"}
        return _enrich(client, "EXACT", 1.0, degraded)

    if mode == "ENTITY_NUMBER":
        cid = _ENTITY_INDEX.get(query.lower())
        if not cid:
            return {"match_type": "NOT_FOUND", "output_completeness": "FULL"}
        return _enrich(CLIENTS[cid], "EXACT", 1.0, degraded)

    # FUZZY_NAME (default)
    q = query.lower()
    if q in _AMBIGUOUS_NAMES:
        return {
            "match_type": "MULTIPLE_CANDIDATES",
            "candidates": _AMBIGUOUS_NAMES[q],
            "output_completeness": "FULL",
        }
    if q in _LEGAL_INDEX:
        return _enrich(CLIENTS[_LEGAL_INDEX[q]], "EXACT", 0.97, degraded)
    if q in _TRADE_INDEX:
        return _enrich(CLIENTS[_TRADE_INDEX[q]], "FUZZY", 0.85, degraded)
    return {"match_type": "NOT_FOUND", "output_completeness": "FULL"}
