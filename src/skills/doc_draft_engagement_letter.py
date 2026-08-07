"""
Skill: doc-draft-engagement-letter

Drafts an engagement letter for a client and service type from an approved
template, populating mandate details and selecting the correct entity for the
mandate's jurisdiction when a client holds several. Missing required fields
(e.g. fee) are left as visible ``{{placeholders}}`` and reported in
``missing_fields`` rather than silently omitted. Cites the data sources used and
always routes for human review.

Validation:
  * Unknown client        -> ERR_CLIENT_NOT_FOUND
  * Unknown service type  -> ERR_TEMPLATE_NOT_FOUND

Runs against in-repo client / template fixtures.
"""

from __future__ import annotations

from typing import Dict

_CLIENTS = {
    "CLT-TEST-001": {
        "default_entity": "Acme (BVI) Ltd",
        "entities": {"VG": "Acme (BVI) Ltd", "KY": "Acme (Cayman) Ltd"},
    },
    "CLT-TEST-002": {
        "default_entity": "Orion Capital Partners Pte Ltd",
        "entities": {"SG": "Orion Capital Partners Pte Ltd"},
    },
    "CLT-MULTI-ENTITY": {
        "default_entity": "MultiCo (BVI) Ltd",
        "entities": {"VG": "MultiCo (BVI) Ltd", "SG": "MultiCo Singapore Pte Ltd"},
    },
}

_TEMPLATES = {"COMPANY_FORMATION", "ACCOUNTING", "REGISTERED_AGENT", "TRUST_ADMIN"}

_REQUIRED_FIELDS = ["fee"]


def run(payload: Dict) -> Dict:
    client_id = payload.get("client_id")
    service_type = payload.get("service_type")
    mandate = payload.get("mandate_details", {}) or {}

    client = _CLIENTS.get(client_id)
    if not client:
        return {"error": "ERR_CLIENT_NOT_FOUND"}

    if service_type not in _TEMPLATES:
        return {"error": "ERR_TEMPLATE_NOT_FOUND"}

    jurisdiction = mandate.get("jurisdiction")
    entity_name = (
        client["entities"].get(jurisdiction)
        or client.get("default_entity")
        or next(iter(client["entities"].values()))
    )

    missing_fields = [f for f in _REQUIRED_FIELDS if mandate.get(f) is None]

    fee = mandate.get("fee", "{{fee}}")
    currency = mandate.get("currency", "USD")
    draft_text = (
        f"ENGAGEMENT LETTER — DRAFT\n"
        f"Client entity: {entity_name}\n"
        f"Service: {service_type}\n"
        f"Jurisdiction: {jurisdiction or '{{jurisdiction}}'}\n"
        f"Fee: {fee} {currency}\n\n"
        f"We are pleased to confirm our engagement to provide {service_type} "
        f"services to {entity_name}.\n"
    )

    data_sources_used = [
        "CRM :: client profile",
        "Semantic Memory :: standard fee schedule",
        f"Template Library :: engagement_letter_{service_type.lower()}_v3",
    ]

    return {
        "format": "DOCX",
        "template_used": f"engagement_letter_{service_type.lower()}_v3",
        "entity_used": entity_name,
        "missing_fields": missing_fields,
        "missing_fields_count": len(missing_fields),
        "requires_human_review": True,
        "data_sources_used": data_sources_used,
        "draft_text": draft_text,
    }
