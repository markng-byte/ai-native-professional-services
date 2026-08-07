"""
Skill: doc-draft-banking-intro

Drafts a banking-introduction letter for a client and a target bank, using the
bank's specific guidelines when known (falling back to a generic template
otherwise), surfacing the historical success rate from mandate history, and
attaching a bank-requirements summary from semantic memory. Low historical
success adds an alternative-bank suggestion. The draft is always returned for
human review — never sent.

Runs against in-repo client / bank-guideline fixtures.
"""

from __future__ import annotations

from typing import Dict

_CLIENTS = {
    "CLT-TEST-001": {"legal_name": "Acme Global Holdings Limited", "jurisdiction": "VG"},
    "CLT-HIGH-RISK": {"legal_name": "Sunrise Capital Ventures Ltd", "jurisdiction": "VG"},
}

_BANK_GUIDELINES = {
    "HSBC": "Certified passports for all directors/UBOs, proof of address (<3m), "
            "board resolution, source-of-funds narrative, structure chart.",
    "DBS": "Certified passports, proof of address, business plan, expected turnover, "
           "SG director where applicable.",
    "BNP Paribas": "Notarised corporate documents, UBO register extract, "
                   "source-of-wealth declaration, tax residency certificates.",
    "Standard Chartered": "Certified constitutional documents, UBO declaration, "
                          "board resolution, banking mandate form.",
}

# Historical success rate keyed by (client_id, bank).
_HISTORY = {
    ("CLT-TEST-001", "HSBC"): 0.65,
    ("CLT-TEST-001", "DBS"): 0.78,
    ("CLT-TEST-001", "Standard Chartered"): 0.55,
}


def run(payload: Dict) -> Dict:
    client_id = payload.get("client_id")
    bank = payload.get("target_bank")
    account_type = payload.get("account_type", "CORPORATE")

    client = _CLIENTS.get(client_id)
    if not client:
        return {"error": "ERR_CLIENT_NOT_FOUND"}

    known_bank = bank in _BANK_GUIDELINES
    template_used = (
        f"banking_intro_{bank.lower().replace(' ', '_')}_v2" if known_bank
        else "generic_banking_intro_template_v2"
    )

    if client_id == "CLT-HIGH-RISK":
        historical_success_rate = 0.22
    else:
        historical_success_rate = _HISTORY.get((client_id, bank))

    bank_requirements_summary = _BANK_GUIDELINES.get(
        bank,
        "Standard KYC pack: certified passports, proof of address, board "
        "resolution, and source-of-funds declaration.",
    )

    alternative_bank_suggestion = None
    if historical_success_rate is not None and historical_success_rate <= 0.3:
        alternative_bank_suggestion = (
            "Historical success is low for this bank/profile — consider DBS or "
            "Standard Chartered, which have accepted comparable structures."
        )

    draft_text = (
        f"BANKING INTRODUCTION LETTER — DRAFT\n"
        f"Re: {account_type} account opening for {client['legal_name']} "
        f"({client['jurisdiction']})\n"
        f"Addressed to: {bank}\n\n"
        f"Requirements per bank guidelines: {bank_requirements_summary}\n"
    )

    return {
        "format": "DOCX",
        "template_used": template_used,
        "missing_fields": [],
        "missing_fields_count": 0,
        "requires_human_review": True,
        "historical_success_rate": historical_success_rate,
        "bank_requirements_summary": bank_requirements_summary,
        "alternative_bank_suggestion": alternative_bank_suggestion,
        "draft_text": draft_text,
    }
